/**
 * ARIA — Calibration
 * calibration.cpp — HX711 + Motor Alignment
 *
 * HX711 calibration:
 *   - Triggered by typing "cal" within 3s of boot
 *   - Multi-point robust fit with MAD outlier rejection
 *   - Prints paste-ready constants
 *
 * Motor alignment (first-boot):
 *   - Triggered by #define MOTOR_ALIGN_MODE
 *   - Detects pole pairs, encoder direction, runs initFOC
 *   - Saves flag to EEPROM — skips on subsequent boots
 *
 * INTEGRATION:
 *   In aria_main.cpp setup():
 *     maybeEnterHX711Cal();    // always call — exits quickly if user doesn't type "cal"
 *     maybeRunMotorAlign();    // always call — skips if EEPROM flag set
 */

#include <Arduino.h>
#include <SimpleFOC.h>
#include <EEPROM.h>

// Uncomment to force motor alignment even if EEPROM flag is set
// #define MOTOR_ALIGN_MODE

#define EEPROM_FLAG_ADDR   0
#define EEPROM_FLAG_VALUE  0xA5

// ── ARIA globals ──
extern BLDCMotor      motor;
extern BLDCDriver3PWM driver;

// HX711 reader class (same as in aria_main.cpp)
class HX711Reader {
public:
    bool ready() const;
    int32_t readRawBlocking(uint32_t timeout_us);
};
extern HX711Reader hx711;

// Output calibration constants here — aria_main.cpp reads these
int32_t CALIB_HX711_OFFSET = 0;
float   CALIB_HX711_SCALE  = 1.0f / 420000.0f;  // placeholder until calibrated


// ═════════════════════════════════════════════
// HX711 CALIBRATION (GPT-4, with MAD outlier rejection)
// ═════════════════════════════════════════════

static constexpr float    G_STD         = 9.80665f;
static constexpr int      MAX_PTS       = 12;
static constexpr int      TARE_SAMPLES  = 200;
static constexpr int      POINT_SAMPLES = 80;
static constexpr uint32_t READ_TIMEOUT  = 30000;

struct CalPoint { float N; int32_t counts; bool inlier; };
static CalPoint pts[MAX_PTS];
static int      numPts = 0;

static void hx_waitEnter() {
    while (true) {
        while (!Serial.available()) delay(5);
        int c = Serial.read();
        if (c == '\n' || c == '\r') return;
    }
}

static bool hx_readLine(char* buf, size_t n) {
    size_t i = 0;
    uint32_t start = millis();
    while (millis() - start < 300000UL) {
        while (Serial.available()) {
            char c = (char)Serial.read();
            if (c == '\r') continue;
            if (c == '\n') { buf[i] = 0; return true; }
            if (i + 1 < n) buf[i++] = c;
        }
        delay(2);
    }
    return false;
}

static bool hx_parseFloat(const char* s, float& out) {
    char* e = nullptr;
    out = strtof(s, &e);
    return e && e != s;
}

static void hx_sortInt(int32_t* a, int n) {
    for (int i = 0; i < n-1; i++)
        for (int j = i+1; j < n; j++)
            if (a[j] < a[i]) { int32_t t=a[i]; a[i]=a[j]; a[j]=t; }
}

static void hx_sortFloat(float* a, int n) {
    for (int i = 0; i < n-1; i++)
        for (int j = i+1; j < n; j++)
            if (a[j] < a[i]) { float t=a[i]; a[i]=a[j]; a[j]=t; }
}

static float hx_median(float* a, int n) {
    hx_sortFloat(a, n);
    if (!n) return 0;
    return (n & 1) ? a[n/2] : 0.5f*(a[n/2-1]+a[n/2]);
}

static bool hx_readAveraged(int32_t& out, int samples, int trim_pct=10) {
    static int32_t buf[512];
    if (samples > 512) samples = 512;
    int got = 0;
    uint32_t start = micros();
    while (got < samples) {
        if (hx711.ready()) {
            buf[got++] = hx711.readRawBlocking(READ_TIMEOUT);
        } else {
            if (micros() - start > 2000000UL) return false;
            delayMicroseconds(200);
        }
    }
    hx_sortInt(buf, got);
    int trimN = (got * trim_pct) / 100;
    int lo = trimN, hi = got - trimN;
    if (hi <= lo) { lo=0; hi=got; }
    int64_t sum = 0;
    for (int i=lo; i<hi; i++) sum += buf[i];
    out = (int32_t)(sum / max(1, hi-lo));
    return true;
}

static bool hx_fitLine(float& a, float& b) {
    double Sx=0,Sy=0,Sxx=0,Sxy=0; int m=0;
    for (int i=0; i<numPts; i++) {
        if (!pts[i].inlier) continue;
        double x=pts[i].counts, y=pts[i].N;
        Sx+=x; Sy+=y; Sxx+=x*x; Sxy+=x*y; m++;
    }
    if (m<2) return false;
    double d = m*Sxx - Sx*Sx;
    if (fabs(d)<1e-12) return false;
    a = (float)((m*Sxy - Sx*Sy)/d);
    b = (float)((Sy*Sxx - Sx*Sxy)/d);
    return true;
}

static bool hx_robustFit(float& a, float& b) {
    for (int i=0; i<numPts; i++) pts[i].inlier = true;
    for (int iter=0; iter<6; iter++) {
        if (!hx_fitLine(a,b)) return false;
        float r[MAX_PTS]; int m=0;
        for (int i=0; i<numPts; i++) {
            if (!pts[i].inlier) continue;
            r[m++] = fabsf(pts[i].N - (a*pts[i].counts+b));
        }
        if (m<3) return true;
        float rc[MAX_PTS]; for (int i=0;i<m;i++) rc[i]=r[i];
        float med = hx_median(rc,m);
        float dev[MAX_PTS]; for (int i=0;i<m;i++) dev[i]=fabsf(r[i]-med);
        float dc[MAX_PTS]; for (int i=0;i<m;i++) dc[i]=dev[i];
        float sigma = hx_median(dc,m) * 1.4826f;
        if (sigma < 1e-6f) return true;
        float thresh = 3.5f * sigma;
        bool changed = false;
        for (int i=0; i<numPts; i++) {
            if (!pts[i].inlier) continue;
            if (fabsf(pts[i].N-(a*pts[i].counts+b)) > thresh) {
                pts[i].inlier=false; changed=true;
            }
        }
        if (!changed) return true;
    }
    return hx_fitLine(a,b);
}

void maybeEnterHX711Cal() {
    Serial.println("Type 'cal' within 3s for HX711 calibration...");
    char buf[16] = {0}; int idx=0;
    uint32_t start = millis();
    while (millis()-start < 3000) {
        if (Serial.available()) {
            char c = (char)Serial.read();
            if (c=='\n'||c=='\r') { buf[idx]=0; break; }
            if (idx<15) buf[idx++]=c;
        }
        delay(2);
    }
    if (strcmp(buf,"cal") != 0) { Serial.println("Skipping HX711 cal."); return; }

    Serial.println("\n=== HX711 Load Cell Calibration ===");
    Serial.println("Commands: add <kg>  addN <N>  list  undo  fit  done  quit\n");

    // Tare
    Serial.println("Remove ALL load. Press ENTER to tare...");
    hx_waitEnter();
    int32_t tare=0;
    if (!hx_readAveraged(tare, TARE_SAMPLES)) {
        Serial.println("ERROR: HX711 read failed during tare."); return;
    }
    Serial.print("Tare offset: "); Serial.println(tare);
    numPts = 0;

    Serial.println("\nHang known weights and record points.");
    Serial.println("Use 4-8 points spanning 5N to max expected tension.\n");

    char line[96];
    while (true) {
        Serial.print("> ");
        if (!hx_readLine(line, sizeof(line))) return;
        char* s = line;
        while (*s==' '||*s=='\t') s++;

        if (!strncmp(s,"quit",4)) { Serial.println("Exiting."); return; }

        if (!strncmp(s,"list",4)) {
            Serial.print("Points: "); Serial.println(numPts);
            for (int i=0;i<numPts;i++) {
                Serial.print(i); Serial.print(": N=");
                Serial.print(pts[i].N,3); Serial.print(" counts=");
                Serial.println(pts[i].counts);
            }
            continue;
        }

        if (!strncmp(s,"undo",4)) {
            if (numPts>0) { numPts--; Serial.println("Removed last point."); }
            else Serial.println("No points.");
            continue;
        }

        bool doFit = !strncmp(s,"fit",3) || !strncmp(s,"done",4);
        if (doFit) {
            if (numPts<2) { Serial.println("Need at least 2 points."); continue; }
            float a=0,b=0;
            if (!hx_robustFit(a,b)) { Serial.println("Fit failed."); continue; }

            // Print table
            Serial.println("\nIdx | Force(N)  | Counts     | Inlier | Residual");
            for (int i=0;i<numPts;i++) {
                float pred = a*pts[i].counts+b;
                Serial.print(i); Serial.print("   | ");
                Serial.print(pts[i].N,3); Serial.print("  | ");
                Serial.print(pts[i].counts); Serial.print("  | ");
                Serial.print(pts[i].inlier?"yes":"NO "); Serial.print("  | ");
                Serial.println(fabsf(pts[i].N-pred),4);
            }

            // Regression offset+scale
            int32_t reg_offset = (fabsf(a)>1e-12f) ? (int32_t)(-b/a) : 0;
            float   reg_scale  = a;

            // Tare-based scale
            double num=0,den=0;
            for (int i=0;i<numPts;i++) {
                if (!pts[i].inlier) continue;
                double x=(double)(pts[i].counts-tare), y=(double)pts[i].N;
                num+=x*y; den+=x*x;
            }
            float tare_scale = (fabs(den)>1e-12) ? (float)(num/den) : 0;

            Serial.println("\n── Paste-ready constants ──");
            Serial.println("// Option A (no tare at boot):");
            Serial.print("int32_t HX711_OFFSET_COUNTS = "); Serial.print(reg_offset); Serial.println(";");
            Serial.print("float   HX711_SCALE_N_PER_COUNT = "); Serial.print(reg_scale,10); Serial.println("f;");
            Serial.println("\n// Option B (tare at every boot — recommended):");
            Serial.print("int32_t HX711_OFFSET_COUNTS = "); Serial.print(tare); Serial.println(";");
            Serial.print("float   HX711_SCALE_N_PER_COUNT = "); Serial.print(tare_scale,10); Serial.println("f;");

            // Update live globals so system can run without reflash
            CALIB_HX711_OFFSET = tare;
            CALIB_HX711_SCALE  = tare_scale;
            Serial.println("\nLive globals updated. Reflash with constants above for persistence.");

            if (!strncmp(s,"done",4)) return;
            continue;
        }

        // addN
        if (!strncmp(s,"addN",4)) {
            if (numPts>=MAX_PTS) { Serial.println("Buffer full."); continue; }
            s+=4; while(*s==' '||*s=='\t') s++;
            float N=0;
            if (!hx_parseFloat(s,N)||N<=0) { Serial.println("Usage: addN <newtons>"); continue; }
            Serial.println("Reading HX711...");
            int32_t c=0;
            if (!hx_readAveraged(c,POINT_SAMPLES)) { Serial.println("Read failed."); continue; }
            pts[numPts++]={N,c,true};
            Serial.print("Recorded: N="); Serial.print(N,3);
            Serial.print(" counts="); Serial.println(c);
            continue;
        }

        // add kg
        if (!strncmp(s,"add",3)) {
            if (numPts>=MAX_PTS) { Serial.println("Buffer full."); continue; }
            s+=3; while(*s==' '||*s=='\t') s++;
            float kg=0;
            if (!hx_parseFloat(s,kg)||kg<=0) { Serial.println("Usage: add <kg>"); continue; }
            float N=kg*G_STD;
            Serial.println("Reading HX711...");
            int32_t c=0;
            if (!hx_readAveraged(c,POINT_SAMPLES)) { Serial.println("Read failed."); continue; }
            pts[numPts++]={N,c,true};
            Serial.print("Recorded: "); Serial.print(kg,3); Serial.print("kg (");
            Serial.print(N,3); Serial.print("N) counts="); Serial.println(c);
            continue;
        }

        Serial.println("Unknown command. Use: add addN list undo fit done quit");
    }
}


// ═════════════════════════════════════════════
// MOTOR ALIGNMENT (first-boot, GPT-4)
// ═════════════════════════════════════════════

#define SUPPLY_VOLTAGE     24.0f
#define OPENLOOP_VOLTAGE   2.0f
#define MAX_PP             30
#define ELEC_SWEEP_REVS    6
#define SWEEP_STEPS        180
#define STEP_DELAY_US      2500
#define DIR_TEST_STEPS     120
#define DIR_TEST_DELAY_US  3000
#define MIN_MECH_DELTA     0.10f

static float angleDiff(float a, float b) {
    float d = a-b;
    while (d>PI) d-=TWO_PI;
    while (d<-PI) d+=TWO_PI;
    return d;
}

static void holdAngle(float elec, float v) {
    motor.setPhaseVoltage(v, 0, elec);
}

static void stopMotor() { driver.setPwm(0,0,0); }

static bool detectDirection(bool& cw) {
    driver.enable();
    float a0 = motor.shaft_angle;
    for (int i=0; i<DIR_TEST_STEPS; i++) {
        float elec = (float)i/DIR_TEST_STEPS * TWO_PI;
        holdAngle(elec, OPENLOOP_VOLTAGE);
        delayMicroseconds(DIR_TEST_DELAY_US);
        motor.sensor->update();
    }
    float a1 = motor.shaft_angle;
    stopMotor(); delay(50);
    float d = angleDiff(a1,a0);
    if (fabsf(d) < MIN_MECH_DELTA) {
        Serial.println("[ALIGN FAIL] Insufficient movement — raise OPENLOOP_VOLTAGE");
        return false;
    }
    cw = (d>0);
    motor.sensor->direction = cw ? Direction::CW : Direction::CCW;
    Serial.print("[ALIGN] Direction: "); Serial.println(cw?"CW":"CCW");
    return true;
}

static bool detectPolePairs(int& pp) {
    driver.enable();
    float prev = motor.shaft_angle;
    float unwrapped = 0;
    int total = ELEC_SWEEP_REVS * SWEEP_STEPS;
    for (int i=0; i<total; i++) {
        float elec = (float)(i%SWEEP_STEPS)/SWEEP_STEPS * TWO_PI;
        holdAngle(elec, OPENLOOP_VOLTAGE);
        delayMicroseconds(STEP_DELAY_US);
        motor.sensor->update();
        float now = motor.shaft_angle;
        unwrapped += angleDiff(now,prev);
        prev = now;
    }
    stopMotor(); delay(100);
    float avg = fabsf(unwrapped)/ELEC_SWEEP_REVS;
    if (avg < 0.05f) {
        Serial.println("[ALIGN FAIL] No mechanical movement — check motor wiring");
        return false;
    }
    float ppf = TWO_PI / avg;
    pp = (int)lroundf(ppf);
    if (pp<1||pp>MAX_PP) {
        Serial.print("[ALIGN FAIL] Pole pairs out of range: "); Serial.println(pp);
        return false;
    }
    Serial.print("[ALIGN] Detected pole pairs: "); Serial.println(pp);
    return true;
}

static bool runFOCInit(int pp) {
    motor.pole_pairs = pp;
    motor.voltage_power_supply = SUPPLY_VOLTAGE;
    motor.voltage_limit = OPENLOOP_VOLTAGE;
    motor.controller = MotionControlType::torque;
    motor.init();
    int result = motor.initFOC();
    if (result != 1) {
        Serial.println("[ALIGN FAIL] initFOC() failed");
        return false;
    }
    Serial.print("[ALIGN] Zero electric angle: ");
    Serial.println(motor.zero_electric_angle, 5);
    return true;
}

static bool verifyClosedLoop() {
    motor.controller = MotionControlType::velocity;
    motor.voltage_limit = OPENLOOP_VOLTAGE;
    motor.velocity_limit = 6.0f;
    float a0 = motor.shaft_angle;
    uint32_t t0 = millis();
    while (millis()-t0 < 700) {
        motor.loopFOC();
        motor.move(3.0f);
    }
    float a1 = motor.shaft_angle;
    motor.move(0);
    for (int i=0;i<200;i++) { motor.loopFOC(); motor.move(0); delayMicroseconds(2000); }
    float d = angleDiff(a1,a0);
    if (fabsf(d)<0.10f) {
        Serial.println("[ALIGN FAIL] Closed loop — no movement");
        return false;
    }
    bool pass = (d>0);
    Serial.print("[ALIGN] Closed loop direction: ");
    Serial.println(pass?"CORRECT":"REVERSED — swap any two motor phases");
    return pass;
}

void maybeRunMotorAlign() {
    EEPROM.begin(64);

#ifdef MOTOR_ALIGN_MODE
    EEPROM.write(EEPROM_FLAG_ADDR, 0x00);
    EEPROM.commit();
    Serial.println("[ALIGN] MOTOR_ALIGN_MODE forced — clearing EEPROM flag");
#endif

    uint8_t flag = EEPROM.read(EEPROM_FLAG_ADDR);
    if (flag == EEPROM_FLAG_VALUE) {
        Serial.println("[ALIGN] Already calibrated — skipping");
        return;
    }

    Serial.println("\n=== Motor First-Boot Alignment ===");
    bool ok = true;

    bool cw = true;
    ok &= detectDirection(cw);

    int pp = -1;
    if (ok) ok &= detectPolePairs(pp);
    if (ok) ok &= runFOCInit(pp);
    if (ok) ok &= verifyClosedLoop();

    if (ok) {
        EEPROM.write(EEPROM_FLAG_ADDR, EEPROM_FLAG_VALUE);
        EEPROM.commit();
        Serial.println("[ALIGN] PASS — saved to EEPROM");
    } else {
        Serial.println("[ALIGN] FAIL — will retry next boot");
        Serial.println("[ALIGN] Check: motor wiring, power supply, OPENLOOP_VOLTAGE");
    }
    Serial.println("=== End Motor Alignment ===\n");
}
