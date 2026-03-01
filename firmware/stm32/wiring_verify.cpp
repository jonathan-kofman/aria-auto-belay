/**
 * ARIA — Wiring Verification Routine
 * wiring_verify.cpp
 *
 * Call verifyWiringAndSensors() from setup() before initFOC().
 * Returns true = all pass, proceed. False = halt.
 *
 * Tests:
 *   1. Motor phases A/B/C (current ADC or BEMF ADC)
 *   2. AS5048A SPI encoder (angle plausibility)
 *   3. HX711 load cell (data ready + non-stuck output)
 *   4. UART to ESP32 (ping/ACK protocol)
 *
 * ARIA PIN ASSIGNMENTS (match aria_main.cpp):
 *   Motor phases:  PA8, PA9, PA10
 *   Driver enable: PB10
 *   Encoder CS:    PA4  (SPI1)
 *   HX711 DOUT:    PB0
 *   HX711 SCK:     PB1
 *   ESP32 UART:    Serial2 (PA2 TX, PA3 RX)
 *
 * Source: GPT-4 generated, integrated into ARIA by Jonathan Kofman
 */

#include <Arduino.h>
#include <SPI.h>

// ─────────────────────────────────────────────
// PIN CONFIG — must match aria_main.cpp
// ─────────────────────────────────────────────

static const uint8_t PIN_U_PWM    = PA8;
static const uint8_t PIN_V_PWM    = PA9;
static const uint8_t PIN_W_PWM    = PA10;
static const uint8_t PIN_DRV_EN   = PB10;
static const uint8_t PIN_ENC_CS   = PA4;
static const uint8_t PIN_HX_DOUT  = PB0;
static const uint8_t PIN_HX_SCK   = PB1;

// ─────────────────────────────────────────────
// PHASE TEST CONFIG
// Choose PHASE_SENSE_CURRENT_ADC if you have a
// current sense shunt wired to an ADC pin.
// Choose PHASE_SENSE_BEMF_ADC if you have phase
// voltage dividers on ADC pins.
// ─────────────────────────────────────────────

enum PhaseSenseMode { PHASE_SENSE_CURRENT_ADC, PHASE_SENSE_BEMF_ADC };
static const PhaseSenseMode PHASE_SENSE_MODE = PHASE_SENSE_CURRENT_ADC;

// ADC pins — set whichever mode you use
static const uint8_t PIN_CURRENT_ADC = PA0;
static const uint8_t PIN_BEMF_U_ADC  = PA1;
static const uint8_t PIN_BEMF_V_ADC  = PA2;
static const uint8_t PIN_BEMF_W_ADC  = PA3;

static const uint16_t PHASE_PULSE_PWM   = 70;   // 0-255, keep small
static const uint16_t PHASE_PULSE_MS    = 12;
static const uint16_t PHASE_SETTLE_MS   = 4;
static const uint16_t PHASE_COOLDOWN_MS = 20;
static const int      CURRENT_DELTA_MIN = 30;   // ADC counts
static const int      BEMF_DELTA_MIN    = 25;

// ─────────────────────────────────────────────
// ESP32 UART PING PROTOCOL
// STM32 sends: [0xAA 0x55 0x01 seq checksum]
// ESP32 replies: [0xAA 0x55 0x81 seq checksum]
// Add the handler to aria_esp32_firmware.ino
// ─────────────────────────────────────────────

static HardwareSerial &ESP_SERIAL      = Serial2;
static const uint32_t  ESP_BAUD        = 115200;
static const uint32_t  ESP_PING_TMO_MS = 200;
static const uint8_t   ESP_PING_RETRY  = 3;
static const uint8_t   PKT0 = 0xAA, PKT1 = 0x55;
static const uint8_t   TYPE_PING = 0x01, TYPE_ACK = 0x81;

static const SPISettings ENC_SPI_SETTINGS(1000000, MSBFIRST, SPI_MODE1);
static const uint32_t    HX_TIMEOUT_US = 250000;

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

static void prtPass(const char* n) { Serial.print("[PASS] "); Serial.println(n); }
static void prtFail(const char* n, const char* d) {
    Serial.print("[FAIL] "); Serial.print(n);
    Serial.print(" → "); Serial.println(d);
}
static void prtHdr(const char* n) {
    Serial.print("\n=== "); Serial.print(n); Serial.println(" ===");
}

static void drvEnable(bool en) {
    if (PIN_DRV_EN == 255) return;
    pinMode(PIN_DRV_EN, OUTPUT);
    digitalWrite(PIN_DRV_EN, en ? HIGH : LOW);
}
static void allPhasesOff() {
    analogWrite(PIN_U_PWM, 0);
    analogWrite(PIN_V_PWM, 0);
    analogWrite(PIN_W_PWM, 0);
}

// ─────────────────────────────────────────────
// MOTOR PHASE TEST
// ─────────────────────────────────────────────

static int readSense(char ph) {
    if (PHASE_SENSE_MODE == PHASE_SENSE_CURRENT_ADC) return analogRead(PIN_CURRENT_ADC);
    switch(ph) {
        case 'U': return analogRead(PIN_BEMF_U_ADC);
        case 'V': return analogRead(PIN_BEMF_V_ADC);
        case 'W': return analogRead(PIN_BEMF_W_ADC);
        default:  return 0;
    }
}

static bool verifyPhase(const char* name, char ph, uint8_t pin) {
    pinMode(pin, OUTPUT); analogWrite(pin, 0);
    delay(PHASE_SETTLE_MS);
    int base = readSense(ph);
    allPhasesOff(); delay(PHASE_SETTLE_MS);
    analogWrite(pin, PHASE_PULSE_PWM); delay(PHASE_PULSE_MS);
    analogWrite(pin, 0);
    delay(PHASE_SETTLE_MS);
    int after = readSense(ph);
    int delta = abs(after - base);
    int minD  = (PHASE_SENSE_MODE==PHASE_SENSE_CURRENT_ADC) ? CURRENT_DELTA_MIN : BEMF_DELTA_MIN;

    if (base==0 && after==0)     { prtFail(name,"ADC reads 0 — short to GND or pin misconfigured"); return false; }
    if (base>=4090 && after>=4090){ prtFail(name,"ADC saturated — short to Vref or divider wrong"); return false; }
    if (delta < minD)             { prtFail(name,"No response — phase open, driver not enabled, or wrong ADC pin"); return false; }
    prtPass(name);
    delay(PHASE_COOLDOWN_MS);
    return true;
}

// ─────────────────────────────────────────────
// AS5048A SPI ENCODER TEST
// ─────────────────────────────────────────────

static uint8_t evenParity16(uint16_t v) {
    v^=v>>8; v^=v>>4; v^=v>>2; v^=v>>1; return v&1;
}
static uint16_t encMakeRead(uint16_t addr) {
    uint16_t cmd = (1u<<14)|(addr&0x3FFF);
    if (evenParity16(cmd)) cmd|=(1u<<15);
    return cmd;
}
static uint16_t encXfer16(uint16_t w) {
    uint8_t rh = SPI.transfer((w>>8)&0xFF);
    uint8_t rl = SPI.transfer(w&0xFF);
    return (uint16_t(rh)<<8)|rl;
}
static uint16_t encReadReg(uint16_t addr) {
    uint16_t cmd = encMakeRead(addr);
    digitalWrite(PIN_ENC_CS, LOW); SPI.beginTransaction(ENC_SPI_SETTINGS);
    encXfer16(cmd);
    digitalWrite(PIN_ENC_CS, HIGH); SPI.endTransaction();
    delayMicroseconds(2);
    digitalWrite(PIN_ENC_CS, LOW); SPI.beginTransaction(ENC_SPI_SETTINGS);
    uint16_t r = encXfer16(0x0000);
    digitalWrite(PIN_ENC_CS, HIGH); SPI.endTransaction();
    return r;
}

static bool verifyEncoder() {
    const char* n = "AS5048A SPI encoder";
    pinMode(PIN_ENC_CS, OUTPUT); digitalWrite(PIN_ENC_CS, HIGH);
    SPI.begin();
    uint16_t r1=encReadReg(0x3FFF), r2=encReadReg(0x3FFF), r3=encReadReg(0x3FFF);
    uint16_t a1=r1&0x3FFF, a2=r2&0x3FFF, a3=r3&0x3FFF;
    if ((r1==0x0000&&r2==0x0000)||(r1==0xFFFF&&r2==0xFFFF)) {
        prtFail(n,"All zeros or all ones — check CS/MOSI/MISO/SCK, SPI mode, power"); return false; }
    if (a1==0&&a2==0&&a3==0) {
        prtFail(n,"Angle stuck at 0 — sensor not powered, MISO stuck low, or magnet missing"); return false; }
    if (a1==0x3FFF&&a2==0x3FFF&&a3==0x3FFF) {
        prtFail(n,"Angle stuck at max — MISO stuck high or wrong SPI mode"); return false; }
    prtPass(n); return true;
}

// ─────────────────────────────────────────────
// HX711 LOAD CELL TEST
// ─────────────────────────────────────────────

static bool hx711Ready() { return digitalRead(PIN_HX_DOUT)==LOW; }
static bool hx711WaitReady(uint32_t tus) {
    uint32_t s=micros();
    while (!hx711Ready()) { if(micros()-s>tus) return false; delayMicroseconds(50); }
    return true;
}
static int32_t hx711Read() {
    uint32_t d=0;
    for (uint8_t i=0;i<24;i++) {
        digitalWrite(PIN_HX_SCK,HIGH); delayMicroseconds(1);
        d=(d<<1)|(digitalRead(PIN_HX_DOUT)?1u:0u);
        digitalWrite(PIN_HX_SCK,LOW); delayMicroseconds(1);
    }
    // gain pulse
    digitalWrite(PIN_HX_SCK,HIGH); delayMicroseconds(1);
    digitalWrite(PIN_HX_SCK,LOW); delayMicroseconds(1);
    if (d&0x800000u) d|=0xFF000000u;
    return (int32_t)d;
}

static bool verifyHX711() {
    const char* n = "HX711 load cell";
    pinMode(PIN_HX_DOUT, INPUT);
    pinMode(PIN_HX_SCK, OUTPUT); digitalWrite(PIN_HX_SCK, LOW);
    if (!hx711WaitReady(HX_TIMEOUT_US)) {
        prtFail(n,"DOUT stayed HIGH — check DOUT/SCK wiring, power, clock not held high"); return false; }
    int32_t v1=hx711Read();
    delay(10);
    if (!hx711WaitReady(HX_TIMEOUT_US)) {
        prtFail(n,"Timed out on second sample — intermittent wiring or bad HX711"); return false; }
    int32_t v2=hx711Read();
    if (v1==0&&v2==0)               { prtFail(n,"Reads 0 twice — DOUT shorted low or SCK not toggling"); return false; }
    if (v1==-1&&v2==-1)             { prtFail(n,"Reads -1 twice — DOUT floating or missing GND"); return false; }
    if (v1==(int32_t)0x7FFFFF||v1==(int32_t)0xFF800000) {
        prtFail(n,"Saturated/extreme — load cell wiring wrong or HX711 inputs floating"); return false; }
    prtPass(n); return true;
}

// ─────────────────────────────────────────────
// ESP32 UART PING TEST
// ─────────────────────────────────────────────

static uint8_t pktCS(const uint8_t* b, size_t n) { uint8_t x=0; for(size_t i=0;i<n;i++) x^=b[i]; return x; }

static bool esp32Ping(uint8_t seq) {
    uint8_t pkt[5]={PKT0,PKT1,TYPE_PING,seq,0};
    pkt[4]=pktCS(pkt,4);
    while(ESP_SERIAL.available()) ESP_SERIAL.read();
    ESP_SERIAL.write(pkt,5); ESP_SERIAL.flush();
    uint32_t t0=millis(); uint8_t buf[5]; size_t idx=0;
    while(millis()-t0<ESP_PING_TMO_MS) {
        while(ESP_SERIAL.available()) {
            uint8_t c=(uint8_t)ESP_SERIAL.read();
            if(idx==0&&c!=PKT0) continue;
            if(idx==1&&c!=PKT1) {idx=0;continue;}
            buf[idx++]=c;
            if(idx==5) {
                if(buf[2]==TYPE_ACK&&buf[3]==seq&&buf[4]==pktCS(buf,4)) return true;
                idx=0;
            }
        }
    }
    return false;
}

static bool verifyESP32() {
    const char* n = "ESP32 UART link";
    ESP_SERIAL.begin(ESP_BAUD);
    for(uint8_t i=0;i<ESP_PING_RETRY;i++) {
        if(esp32Ping((uint8_t)(millis()&0xFF))) { prtPass(n); return true; }
        delay(30);
    }
    prtFail(n,"No ACK — check TX/RX cross-wiring, baud rate, shared GND, ESP32 ping handler in firmware");
    return false;
}

// ─────────────────────────────────────────────
// PUBLIC ENTRY POINT
// ─────────────────────────────────────────────

bool verifyWiringAndSensors() {
    prtHdr("ARIA Boot Wiring Verification");
    analogWriteResolution(8);

    // Motor phases
    prtHdr("Motor Phases");
    pinMode(PIN_U_PWM,OUTPUT); pinMode(PIN_V_PWM,OUTPUT); pinMode(PIN_W_PWM,OUTPUT);
    drvEnable(true); delay(10);
    bool ok = true;
    ok &= verifyPhase("Phase U", 'U', PIN_U_PWM);
    ok &= verifyPhase("Phase V", 'V', PIN_V_PWM);
    ok &= verifyPhase("Phase W", 'W', PIN_W_PWM);
    allPhasesOff(); drvEnable(false);

    // Encoder
    prtHdr("Encoder"); ok &= verifyEncoder();

    // Load cell
    prtHdr("Load Cell"); ok &= verifyHX711();

    // ESP32
    prtHdr("ESP32 UART"); ok &= verifyESP32();

    // Summary
    prtHdr("Summary");
    if(ok) { Serial.println("ALL PASS — proceeding to FOC init"); return true; }
    else   { Serial.println("FAIL — fix wiring and reboot"); return false; }
}
