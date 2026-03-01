/**
 * ARIA — aria_main.cpp
 * Main firmware entry point — ties all modules together.
 *
 * File structure:
 *   aria_main.cpp     ← this file (state machine + motor control)
 *   safety.h/.cpp     ← watchdog + fault recovery
 *   calibration.cpp   ← HX711 cal + motor alignment
 *
 * FIRST TIME SETUP ORDER:
 *   1. Flash firmware
 *   2. Open serial at 115200
 *   3. Type "cal" within 3s → calibrate load cell
 *   4. Copy output constants into HX711_OFFSET / HX711_SCALE below
 *   5. Reflash — motor alignment runs automatically (first boot only)
 *   6. Normal operation begins
 *
 * TO FORCE MOTOR REALIGNMENT:
 *   Uncomment #define MOTOR_ALIGN_MODE in calibration.cpp and reflash
 */

#include <Arduino.h>
#include <SPI.h>
#include <SimpleFOC.h>
#include "safety.h"

// ─────────────────────────────────────────────
// CONFIGURE THESE
// ─────────────────────────────────────────────

// Pins
static constexpr uint8_t PIN_AS5048_CS  = PA4;
static constexpr uint8_t PIN_HX711_DOUT = PB0;
static constexpr uint8_t PIN_HX711_SCK  = PB1;
static constexpr uint8_t PIN_UH         = PA8;
static constexpr uint8_t PIN_VH         = PA9;
static constexpr uint8_t PIN_WH         = PA10;
static constexpr uint8_t PIN_EN         = PB10;
static constexpr uint8_t PIN_LED        = PC13;
static constexpr uint8_t PIN_ESTOP      = PB12;

// Calibration constants — paste from "cal" routine output
static int32_t HX711_OFFSET = 0;            // ← paste here after calibration
static float   HX711_SCALE  = 1.0f/420000.0f; // ← paste here after calibration

// Hardware
static constexpr float   SUPPLY_V      = 24.0f;
static constexpr float   VOLTAGE_LIMIT = 10.0f;
static constexpr int     POLE_PAIRS    = 7;   // overwritten by motor alignment
static constexpr float   GEAR_RATIO    = 30.0f;
static constexpr float   SPOOL_R       = 0.30f;

// ARIA behavior
static constexpr float   T_BASELINE    = 40.0f;
static constexpr float   T_WATCH_ME    = 25.0f;
static constexpr float   T_TAKE        = 200.0f;
static constexpr float   T_FALL        = 400.0f;
static constexpr float   T_GROUND      = 15.0f;
static constexpr float   CLIP_CONF_MIN = 0.75f;
static constexpr float   CLIP_SLACK_M  = 0.65f;
static constexpr float   SPD_LOWER     = 0.5f;
static constexpr float   SPD_RETRACT   = 0.8f;
static constexpr float   SPD_FALL      = 2.0f;
static constexpr uint32_t TAKE_CONF_MS = 500;
static constexpr uint32_t WATCH_MS     = 180000UL;
static constexpr uint32_t REST_MS      = 600000UL;
static constexpr uint32_t CTRL_HZ      = 20;
static constexpr uint32_t HX_HZ        = 200;


// ─────────────────────────────────────────────
// STATE MACHINE
// ─────────────────────────────────────────────

typedef enum : uint8_t {
    STATE_IDLE=0, STATE_CLIMBING=1, STATE_CLIPPING=2,
    STATE_TAKE=3, STATE_REST=4,    STATE_LOWER=5,
    STATE_WATCH_ME=6, STATE_UP=7,  STATE_ESTOP=8
} ARIAState;

typedef enum : uint8_t {
    CMD_NONE=0,CMD_TAKE=1,CMD_SLACK=2,CMD_LOWER=3,
    CMD_UP=4,CMD_WATCH_ME=5,CMD_REST=6,CMD_CLIMBING=7
} VoiceCmd;

typedef enum : uint8_t {
    MOTOR_HOLD=0,MOTOR_PAYOUT=1,MOTOR_RETRACT=2,MOTOR_TENSION=3
} MotorMode;


// ─────────────────────────────────────────────
// HX711 DRIVER
// ─────────────────────────────────────────────

class HX711Reader {
public:
    HX711Reader(uint8_t dout, uint8_t sck) : _d(dout),_s(sck) {}
    void begin() {
        pinMode(_d,INPUT_PULLUP);
        pinMode(_s,OUTPUT);
        digitalWrite(_s,LOW);
    }
    bool ready() const { return digitalRead(_d)==LOW; }
    int32_t readRawBlocking(uint32_t timeout_us=2000) {
        uint32_t start=micros();
        while(!ready()) { if(micros()-start>timeout_us) return _last; }
        int32_t v=0;
        noInterrupts();
        for(int i=0;i<24;i++){
            digitalWrite(_s,HIGH); delayMicroseconds(1);
            v=(v<<1)|(digitalRead(_d)?1:0);
            digitalWrite(_s,LOW); delayMicroseconds(1);
        }
        digitalWrite(_s,HIGH); delayMicroseconds(1);
        digitalWrite(_s,LOW);
        interrupts();
        if(v&0x800000) v|=~0xFFFFFF;
        _last=v; return v;
    }
private:
    uint8_t _d,_s;
    int32_t _last=0;
};

HX711Reader hx711(PIN_HX711_DOUT, PIN_HX711_SCK);

// Declared in calibration.cpp — updated by cal routine
extern int32_t CALIB_HX711_OFFSET;
extern float   CALIB_HX711_SCALE;


// ─────────────────────────────────────────────
// SIMPLEFOC OBJECTS
// ─────────────────────────────────────────────

MagneticSensorSPI sensor = MagneticSensorSPI(AS5048_SPI, PIN_AS5048_CS);
BLDCMotor         motor(POLE_PAIRS);
BLDCDriver3PWM    driver(PIN_UH, PIN_VH, PIN_WH, PIN_EN);


// ─────────────────────────────────────────────
// TENSION PID (GPT-4 structure)
// ─────────────────────────────────────────────

struct PID {
    float kp,ki,kd,i=0,le=0,out_limit=VOLTAGE_LIMIT,i_limit=0.5f,dlpf=0.05f,ds=0;
    float step(float e, float dt) {
        i=constrain(i+e*dt*ki,-i_limit,i_limit);
        float de=(dt>1e-6f)?(e-le)/dt:0;
        ds=ds+dlpf*(de-ds); le=e;
        return constrain(kp*e+i+kd*ds,-out_limit,out_limit);
    }
    void reset(){i=0;le=0;ds=0;}
};

// Starting gains — auto-tuner will improve these
PID tensionPID{.kp=0.08f,.ki=1.5f,.kd=0.0005f};
LowPassFilter tensionLPF(0.02f);


// ─────────────────────────────────────────────
// GLOBALS
// ─────────────────────────────────────────────

ARIAState g_state      = STATE_IDLE;
MotorMode g_motorMode  = MOTOR_HOLD;
float     g_tension    = 0.0f;
float     g_ropePos    = 0.0f;
float     g_ropeSpeed  = 0.0f;
uint32_t  g_stateMs    = 0;
uint32_t  g_takeMs     = 0;
uint32_t  g_clipMs     = 0;
bool      g_takePend   = false;

// From ESP32
float    g_cvHeight    = 0.0f;
float    g_cvClip      = 0.0f;
bool     g_cvDetected  = false;
VoiceCmd g_voiceCmd    = CMD_NONE;
float    g_voiceConf   = 0.0f;

// UART
HardwareSerial ESP32Serial(2);
char    g_ubuf[64];
uint8_t g_uidx = 0;

// Timing
uint32_t g_lastCtrl = 0;
uint32_t g_lastHX   = 0;


// ─────────────────────────────────────────────
// FORWARD DECLARATIONS (calibration.cpp)
// ─────────────────────────────────────────────

void maybeEnterHX711Cal();
void maybeRunMotorAlign();
void Safety_NotifyHX711Ok();  // in safety.cpp


// ─────────────────────────────────────────────
// UART
// ─────────────────────────────────────────────

void uart_tx() {
    char b[64];
    snprintf(b,sizeof(b),"S:%d:%.1f:%.2f:%d\n",
             (int)g_state,g_tension,g_ropePos,(int)g_motorMode);
    ESP32Serial.print(b);
}

void uart_parse(const char* p) {
    if(p[0]=='V'){
        int c; float conf;
        if(sscanf(p+2,"%d:%f",&c,&conf)==2){
            g_voiceCmd=(VoiceCmd)c; g_voiceConf=conf;
            g_lastEsp32RxMs=millis();  // notify safety layer
        }
    } else if(p[0]=='C'){
        float clip,h; int det;
        if(sscanf(p+2,"%f:%f:%d",&clip,&h,&det)==3){
            g_cvClip=clip; g_cvHeight=h; g_cvDetected=(bool)det;
            g_lastEsp32RxMs=millis();
        }
    }
    // PID tuner support — added for aria_pid_tuner.py
    else if(p[0]=='P'){
        float kp,ki,kd;
        if(sscanf(p+2,"%f:%f:%f",&kp,&ki,&kd)==3){
            tensionPID.kp=kp; tensionPID.ki=ki; tensionPID.kd=kd;
            tensionPID.reset();
            Serial.println("[PID] Gains updated from tuner");
        }
    }
    else if(p[0]=='T'){
        // Setpoint override for PID tuner step tests
        // Handled implicitly via state machine setpoint
        // Future: add g_tension_setpoint override
    }
}

void uart_read() {
    while(ESP32Serial.available()){
        char c=(char)ESP32Serial.read();
        if(c=='\n'){g_ubuf[g_uidx]='\0';uart_parse(g_ubuf);g_uidx=0;}
        else if(g_uidx<63) g_ubuf[g_uidx++]=c;
    }
}


// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

bool validVoice(VoiceCmd cmd){return g_voiceCmd==cmd&&g_voiceConf>=0.85f;}
uint32_t timeInState(){return millis()-g_stateMs;}
float mpsToRads(float mps){return (mps/max(SPOOL_R,1e-6f))*GEAR_RATIO;}

void setState(ARIAState s){
    if(s==g_state) return;
    g_state=s; g_stateMs=millis();
    tensionPID.reset();
    Serial.print("STATE→"); Serial.println((int)s);
    uart_tx();
}

void motorHold(){g_motorMode=MOTOR_HOLD; motor.move(0);}
void motorPayout(float mps){
    g_motorMode=MOTOR_PAYOUT;
    motor.controller=MotionControlType::velocity;
    motor.move(mpsToRads(mps));
}
void motorRetract(float mps){
    g_motorMode=MOTOR_RETRACT;
    motor.controller=MotionControlType::velocity;
    motor.move(-mpsToRads(mps));
}
void motorTension(float target_n, float dt){
    g_motorMode=MOTOR_TENSION;
    motor.controller=MotionControlType::torque;
    float e=target_n-g_tension;
    if(fabsf(e)<0.5f) e=0;
    motor.move(tensionPID.step(e,dt));
}


// ─────────────────────────────────────────────
// STATE HANDLERS
// ─────────────────────────────────────────────

void handleIdle(){
    motorHold();
    if(g_cvDetected && g_tension>T_GROUND) setState(STATE_CLIMBING);
}

void handleClimbing(float dt){
    motorTension(T_BASELINE,dt);
    if(g_tension<T_GROUND && !g_cvDetected){setState(STATE_IDLE);return;}
    if(g_cvClip>=CLIP_CONF_MIN){g_clipMs=millis();setState(STATE_CLIPPING);return;}
    if(validVoice(CMD_TAKE)){g_takeMs=millis();g_takePend=true;setState(STATE_TAKE);return;}
    if(validVoice(CMD_REST)){setState(STATE_REST);return;}
    if(validVoice(CMD_LOWER)){setState(STATE_LOWER);return;}
    if(validVoice(CMD_WATCH_ME)){setState(STATE_WATCH_ME);return;}
    if(validVoice(CMD_UP)){setState(STATE_UP);return;}
}

void handleClipping(){
    float dur=(CLIP_SLACK_M/0.3f)*1000.0f;
    if((millis()-g_clipMs)<(uint32_t)dur) motorPayout(0.8f);
    else setState(STATE_CLIMBING);
}

void handleTake(){
    if(g_takePend){
        if((millis()-g_takeMs)<=TAKE_CONF_MS){
            if(g_tension>=T_TAKE){g_takePend=false;motorRetract(SPD_RETRACT);return;}
        } else {
            g_takePend=false; setState(STATE_CLIMBING); return;
        }
    }
    motorHold();
    if(validVoice(CMD_CLIMBING)){setState(STATE_CLIMBING);return;}
    if(g_ropeSpeed>0.1f&&g_tension<T_TAKE){setState(STATE_CLIMBING);return;}
    if(timeInState()>REST_MS) setState(STATE_CLIMBING);
}

void handleRest(){
    motorHold();
    if(validVoice(CMD_CLIMBING)){setState(STATE_CLIMBING);return;}
    if(g_ropeSpeed>0.1f){setState(STATE_CLIMBING);return;}
    if(timeInState()>REST_MS) setState(STATE_CLIMBING);
}

void handleLower(){
    if(g_tension>T_FALL){setState(STATE_CLIMBING);return;}
    motorPayout(SPD_LOWER);
    if(g_tension<T_GROUND) setState(STATE_IDLE);
}

void handleWatchMe(float dt){
    motorTension(T_WATCH_ME,dt);
    if(validVoice(CMD_TAKE)){g_takeMs=millis();g_takePend=true;setState(STATE_TAKE);return;}
    if(validVoice(CMD_LOWER)){setState(STATE_LOWER);return;}
    if(validVoice(CMD_CLIMBING)){setState(STATE_CLIMBING);return;}
    if(timeInState()>WATCH_MS) setState(STATE_CLIMBING);
}

void handleUp(float dt){
    motorTension(5.0f,dt);
    if(g_tension<-5.0f) motorHold();
    if(validVoice(CMD_CLIMBING)){setState(STATE_CLIMBING);return;}
    if(validVoice(CMD_TAKE)){g_takeMs=millis();g_takePend=true;setState(STATE_TAKE);}
}

void handleEstop(){
    motorHold(); motor.disable();
    digitalWrite(PIN_LED,LOW);
}


// ─────────────────────────────────────────────
// SETUP
// ─────────────────────────────────────────────

void setup(){
    Serial.begin(115200);
    delay(300);
    Serial.println("ARIA Firmware v0.3 — modular");

    pinMode(PIN_LED,OUTPUT); digitalWrite(PIN_LED,HIGH);
    pinMode(PIN_ESTOP,INPUT_PULLUP);

    // HX711 calibration (type "cal" within 3s)
    hx711.begin();
    maybeEnterHX711Cal();

    // Apply calibration constants
    // If user ran cal, CALIB_* are updated. Otherwise use hardcoded values above.
    HX711_OFFSET = CALIB_HX711_OFFSET ? CALIB_HX711_OFFSET : HX711_OFFSET;
    HX711_SCALE  = CALIB_HX711_SCALE  ? CALIB_HX711_SCALE  : HX711_SCALE;

    // UART to ESP32
    ESP32Serial.begin(115200, SERIAL_8N1, PA3, PA2);

    // Motor hardware init
    SPI.begin();
    sensor.init();
    motor.linkSensor(&sensor);
    driver.voltage_power_supply = SUPPLY_V;
    driver.init();
    motor.linkDriver(&driver);
    motor.torque_controller = TorqueControlType::voltage;
    motor.controller        = MotionControlType::torque;
    motor.voltage_limit     = VOLTAGE_LIMIT;
    motor.velocity_limit    = 200.0f;
    motor.LPF_velocity.Tf   = 0.01f;
    motor.PID_velocity.P    = 0.2f;
    motor.PID_velocity.I    = 2.0f;
    motor.P_angle.P         = 10.0f;
    motor.init();

    // Motor alignment (first boot only, saves to EEPROM)
    maybeRunMotorAlign();

    // initFOC after alignment
    motor.initFOC();

    // Safety layer (watchdog + fault detection)
    Safety_Init();

    g_stateMs = millis();
    Serial.println("ARIA ready.");

    for(int i=0;i<3;i++){
        digitalWrite(PIN_LED,LOW); delay(150);
        digitalWrite(PIN_LED,HIGH); delay(150);
    }
}


// ─────────────────────────────────────────────
// MAIN LOOP
// ─────────────────────────────────────────────

void loop(){
    motor.loopFOC();

    uint32_t now_us = micros();

    // HX711 at ~200Hz
    if((now_us-g_lastHX)>=(1000000UL/HX_HZ)){
        g_lastHX=now_us;
        int32_t raw=hx711.readRawBlocking(2000);
        float t=(float)(raw-HX711_OFFSET)*HX711_SCALE;
        g_tension=tensionLPF(t);
        Safety_NotifyHX711Ok();  // tell safety layer HX711 is alive
    }

    // Kinematics
    g_ropeSpeed=(motor.shaft_velocity/GEAR_RATIO)*SPOOL_R;
    g_ropePos  +=(g_ropeSpeed)*(1.0f/1000.0f);
    if(g_ropePos<0) g_ropePos=0;

    // Control loop at CTRL_HZ
    if((now_us-g_lastCtrl)>=(1000000UL/CTRL_HZ)){
        float dt=(now_us-g_lastCtrl)*1e-6f;
        g_lastCtrl=now_us;

        uart_read();

        // Safety layer — runs first, kicks watchdog
        Safety_Update();

        // Hard e-stop check
        if(digitalRead(PIN_ESTOP)==LOW||Safety_IsEstop()||g_state==STATE_ESTOP){
            setState(STATE_ESTOP); handleEstop();
            g_voiceCmd=CMD_NONE; return;
        }

        // Fall detection override
        if(g_ropeSpeed>SPD_FALL && g_tension>T_FALL){
            motorHold();  // clutch handles arrest
            g_voiceCmd=CMD_NONE; return;
        }

        // State machine
        switch(g_state){
            case STATE_IDLE:      handleIdle();        break;
            case STATE_CLIMBING:  handleClimbing(dt);  break;
            case STATE_CLIPPING:  handleClipping();    break;
            case STATE_TAKE:      handleTake();        break;
            case STATE_REST:      handleRest();        break;
            case STATE_LOWER:     handleLower();       break;
            case STATE_WATCH_ME:  handleWatchMe(dt);   break;
            case STATE_UP:        handleUp(dt);        break;
            default: break;
        }

        g_voiceCmd=CMD_NONE; g_voiceConf=0;

        // Send state to ESP32 every 5 ticks
        static uint8_t txc=0;
        if(++txc>=5){txc=0;uart_tx();}
    }
}
