/**
 * ARIA — Safety Layer
 * safety.cpp — Watchdog + Fault Recovery Implementation
 *
 * Integrates GPT-4's fault system with ARIA's motor/sensor globals.
 *
 * Fault types detected:
 *   1. Motor overcurrent (estimated from voltage command magnitude)
 *   2. Encoder dropout (stale AS5048A angle reading)
 *   3. HX711 dropout (load cell timeout)
 *   4. ESP32 UART timeout (no heartbeat from intelligence layer)
 *   5. Prior IWDG reset (detected at boot via RCC flags)
 *
 * Each fault:
 *   - Logs to Serial
 *   - Attempts ONE recovery
 *   - If recovery fails → ESTOP + motor.disable()
 *   - ESTOP latches until power cycle
 */

#include "safety.h"
#include <Arduino.h>
#include <SimpleFOC.h>
#include <math.h>

// ── Forward declarations of ARIA globals (defined in aria_main.cpp) ──
extern BLDCMotor      motor;
extern BLDCDriver3PWM driver;
extern float          g_tension;     // latest load cell reading

// HX711 reader — same class as in aria_main.cpp
class HX711Reader;
extern HX711Reader hx711;

// ─────────────────────────────────────────────
// GLOBALS
// ─────────────────────────────────────────────

volatile uint32_t g_lastEsp32RxMs = 0;


// ─────────────────────────────────────────────
// FAULT TYPES
// ─────────────────────────────────────────────

enum class FaultType : uint8_t {
    NONE                  = 0,
    MOTOR_OVERCURRENT_EST = 1,
    ENCODER_DROPOUT       = 2,
    HX711_DROPOUT         = 3,
    ESP32_UART_TIMEOUT    = 4,
    IWDG_PREV_BOOT        = 5,
    BOOT_SEQUENCE_FAIL    = 6,
};

static const char* FaultName(FaultType f) {
    switch (f) {
        case FaultType::NONE:                  return "NONE";
        case FaultType::MOTOR_OVERCURRENT_EST: return "MOTOR_OVERCURRENT";
        case FaultType::ENCODER_DROPOUT:       return "ENCODER_DROPOUT";
        case FaultType::HX711_DROPOUT:         return "HX711_DROPOUT";
        case FaultType::ESP32_UART_TIMEOUT:    return "ESP32_UART_TIMEOUT";
        case FaultType::IWDG_PREV_BOOT:        return "IWDG_PREV_BOOT";
        case FaultType::BOOT_SEQUENCE_FAIL:    return "BOOT_SEQUENCE_FAIL";
        default:                               return "UNKNOWN";
    }
}

enum class SystemState : uint8_t { RUN = 0, ESTOP = 1 };


// ─────────────────────────────────────────────
// FAULT CONFIG — tune these
// ─────────────────────────────────────────────

struct FaultConfig {
    float    v_mag_limit         = 9.0f;    // V — voltage command magnitude limit
    uint32_t v_mag_trip_ms       = 50;      // must exceed for this long
    float    encoder_stale_eps   = 1e-4f;   // rad — "no change" threshold
    uint32_t encoder_stale_ms    = 150;     // stale for this long
    uint32_t hx711_timeout_ms    = 300;     // no HX711 read within this
    uint32_t esp32_timeout_ms    = 1000;    // no ESP32 packet within this
    uint32_t recovery_grace_ms   = 250;     // time to prove recovery worked
};

static FaultConfig g_cfg;


// ─────────────────────────────────────────────
// RUNTIME STATE
// ─────────────────────────────────────────────

struct FaultRuntime {
    SystemState state              = SystemState::RUN;
    FaultType   active_fault       = FaultType::NONE;
    bool        recovery_attempted = false;
    uint32_t    fault_start_ms     = 0;
    uint32_t    vmag_over_start_ms = 0;
    float       last_angle         = 0.0f;
    uint32_t    last_angle_ms      = 0;
    uint32_t    last_hx711_ok_ms   = 0;
    uint32_t    last_esp32_ok_ms   = 0;
};

static FaultRuntime g_rt;

// Boot sequencing flags — set from aria_main.cpp via Safety_BootMark*.
static bool g_bootHX711Ok   = false;
static bool g_bootEncoderOk = false;
static bool g_bootUartOk    = false;
static bool g_bootMotorOk   = false;
static bool g_bootComplete  = false;

// Brake GPIO — mechanical brake is held *engaged* (HIGH) during boot.
// If your board uses a different pin, override PIN_BRAKE at compile time.
#ifndef PIN_BRAKE
#define PIN_BRAKE PB13
#endif


// ─────────────────────────────────────────────
// IWDG — Hardware Watchdog (~1 second timeout)
// ─────────────────────────────────────────────

static IWDG_HandleTypeDef hiwdg;

static bool IWDG_Init() {
    // LSI ~32kHz, prescaler 64 → 500Hz tick, reload 500 → ~1.0s timeout
    __HAL_RCC_LSI_ENABLE();
    uint32_t t = HAL_GetTick();
    while (__HAL_RCC_GET_FLAG(RCC_FLAG_LSIRDY) == RESET) {
        if (HAL_GetTick() - t > 100) return false;
    }
    hiwdg.Instance       = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_64;
    hiwdg.Init.Reload    = 500;
    hiwdg.Init.Window    = IWDG_WINDOW_DISABLE;
    return HAL_IWDG_Init(&hiwdg) == HAL_OK;
}

static void IWDG_Kick() {
    HAL_IWDG_Refresh(&hiwdg);
}

static bool Boot_WasIwdgReset() {
    bool was = (__HAL_RCC_GET_FLAG(RCC_FLAG_IWDGRST) != RESET);
    __HAL_RCC_CLEAR_RESET_FLAGS();
    return was;
}


// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

static float GetVoltageMagnitude() {
    float vq = motor.voltage.q;
    float vd = motor.voltage.d;
    return sqrtf(vq*vq + vd*vd);
}

static void EnterEstop(FaultType reason) {
    g_rt.state        = SystemState::ESTOP;
    g_rt.active_fault = reason;
    motor.move(0.0f);
    motor.disable();
    driver.disable();
    Serial.print("[ESTOP] Fault: ");
    Serial.println(FaultName(reason));
}


// ─────────────────────────────────────────────
// FAULT DETECTION
// ─────────────────────────────────────────────

static FaultType DetectFault(uint32_t now) {
    if (g_rt.state == SystemState::ESTOP) return FaultType::NONE;

    // 1. Overcurrent estimate
    {
        float vmag = GetVoltageMagnitude();
        if (vmag > g_cfg.v_mag_limit) {
            if (!g_rt.vmag_over_start_ms) g_rt.vmag_over_start_ms = now;
            if ((now - g_rt.vmag_over_start_ms) >= g_cfg.v_mag_trip_ms)
                return FaultType::MOTOR_OVERCURRENT_EST;
        } else {
            g_rt.vmag_over_start_ms = 0;
        }
    }

    // 2. Encoder dropout
    {
        float a = motor.shaft_angle;
        if (fabsf(a - g_rt.last_angle) > g_cfg.encoder_stale_eps) {
            g_rt.last_angle    = a;
            g_rt.last_angle_ms = now;
        } else if (motor.enabled &&
                   (now - g_rt.last_angle_ms) >= g_cfg.encoder_stale_ms) {
            return FaultType::ENCODER_DROPOUT;
        }
    }

    // 3. HX711 dropout — updated from main loop via Safety_NotifyHX711Ok()
    if ((now - g_rt.last_hx711_ok_ms) >= g_cfg.hx711_timeout_ms)
        return FaultType::HX711_DROPOUT;

    // 4. ESP32 UART timeout
    {
        uint32_t last = g_lastEsp32RxMs;
        if (last) g_rt.last_esp32_ok_ms = last;
        if ((now - g_rt.last_esp32_ok_ms) >= g_cfg.esp32_timeout_ms)
            return FaultType::ESP32_UART_TIMEOUT;
    }

    return FaultType::NONE;
}


// ─────────────────────────────────────────────
// RECOVERY
// ─────────────────────────────────────────────

static bool AttemptRecovery(FaultType f) {
    Serial.print("[RECOVER] Attempting: "); Serial.println(FaultName(f));

    switch (f) {
        case FaultType::MOTOR_OVERCURRENT_EST:
            motor.disable(); driver.disable();
            motor.voltage.q = 0; motor.voltage.d = 0;
            HAL_Delay(10);
            driver.enable(); motor.enable();
            return true;

        case FaultType::ENCODER_DROPOUT:
            // Re-init sensor linkage
            motor.linkSensor(motor.sensor);
            return true;

        case FaultType::HX711_DROPOUT:
            // Caller (main loop) should re-init HX711 if this returns true
            // We log and give it a grace period
            Serial.println("[RECOVER] HX711 — waiting for recovery");
            return true;

        case FaultType::ESP32_UART_TIMEOUT:
            // Log — UART recovery is handled at hardware level
            // In Phase 2 (motor only) this fault is disabled
            Serial.println("[RECOVER] ESP32 timeout — waiting for reconnect");
            g_rt.last_esp32_ok_ms = HAL_GetTick(); // give grace period
            return true;

        case FaultType::IWDG_PREV_BOOT:
            // Log only — not actionable
            Serial.println("[BOOT] Prior IWDG reset detected — continuing");
            return true;

        default:
            return false;
    }
}

static bool RecoveryProvedOk(FaultType f, uint32_t now) {
    switch (f) {
        case FaultType::MOTOR_OVERCURRENT_EST:
            return GetVoltageMagnitude() <= g_cfg.v_mag_limit;
        case FaultType::ENCODER_DROPOUT:
            return fabsf(motor.shaft_angle - g_rt.last_angle)
                   > g_cfg.encoder_stale_eps;
        case FaultType::HX711_DROPOUT:
            return (now - g_rt.last_hx711_ok_ms) <= g_cfg.hx711_timeout_ms;
        case FaultType::ESP32_UART_TIMEOUT:
            return (now - g_rt.last_esp32_ok_ms) <= g_cfg.esp32_timeout_ms;
        case FaultType::IWDG_PREV_BOOT:
            return true;
        default:
            return true;
    }
}

static void HandleFault(FaultType f, uint32_t now) {
    if (f == FaultType::NONE) return;
    if (g_rt.active_fault != FaultType::NONE &&
        g_rt.active_fault != f) return;

    if (g_rt.active_fault == FaultType::NONE) {
        g_rt.active_fault       = f;
        g_rt.recovery_attempted = false;
        g_rt.fault_start_ms     = now;
        Serial.print("[FAULT] "); Serial.println(FaultName(f));
    }

    if (!g_rt.recovery_attempted) {
        g_rt.recovery_attempted = true;
        if (!AttemptRecovery(f)) { EnterEstop(f); return; }
    }

    if ((now - g_rt.fault_start_ms) >= g_cfg.recovery_grace_ms) {
        if (RecoveryProvedOk(f, now)) {
            Serial.println("[RECOVER] Success — returning to RUN");
            g_rt.active_fault       = FaultType::NONE;
            g_rt.recovery_attempted = false;
            g_rt.fault_start_ms     = 0;
        } else {
            Serial.println("[RECOVER] Failed — ESTOP");
            EnterEstop(f);
        }
    }
}


// ─────────────────────────────────────────────
// BOOT SEQUENCE API
// ─────────────────────────────────────────────

void Safety_BootBegin() {
    // Step 1: engage brake before any other initialization.
    pinMode(PIN_BRAKE, OUTPUT);
    digitalWrite(PIN_BRAKE, HIGH);  // HIGH = brake engaged
    Serial.println("[BOOT] Brake engaged (PIN_BRAKE HIGH)");

    g_bootHX711Ok   = false;
    g_bootEncoderOk = false;
    g_bootUartOk    = false;
    g_bootMotorOk   = false;
    g_bootComplete  = false;
}

void Safety_BootMarkHX711Ok()   { g_bootHX711Ok   = true; }
void Safety_BootMarkEncoderOk() { g_bootEncoderOk = true; }
void Safety_BootMarkUartOk()    { g_bootUartOk    = true; }
void Safety_BootMarkMotorOk()   { g_bootMotorOk   = true; }

void Safety_BootComplete() {
    // Sequence documented in safety.h:
    // brake on → HX711 → encoder → UART → motor → first heartbeat (from main) → brake off.
    if (g_bootHX711Ok && g_bootEncoderOk && g_bootUartOk && g_bootMotorOk) {
        digitalWrite(PIN_BRAKE, LOW);  // release brake
        g_bootComplete = true;
        Serial.println("[BOOT] All init OK — brake released");
    } else {
        // Missing one or more boot flags — stay in FAULT with brake engaged.
        g_bootComplete = false;
        EnterEstop(FaultType::BOOT_SEQUENCE_FAIL);
        digitalWrite(PIN_BRAKE, HIGH);
        Serial.println("[BOOT] Sequence incomplete — staying in ESTOP with brake engaged");
    }
}


// ─────────────────────────────────────────────
// PUBLIC API
// ─────────────────────────────────────────────

bool Safety_Init() {
    uint32_t now = HAL_GetTick();
    g_rt.last_angle         = motor.shaft_angle;
    g_rt.last_angle_ms      = now;
    g_rt.last_hx711_ok_ms   = now;
    g_rt.last_esp32_ok_ms   = now;
    g_lastEsp32RxMs         = now;

    if (Boot_WasIwdgReset()) {
        Serial.println("[BOOT] Prior IWDG reset detected");
        g_rt.active_fault       = FaultType::IWDG_PREV_BOOT;
        g_rt.recovery_attempted = false;
        g_rt.fault_start_ms     = now;
    }

    if (!IWDG_Init()) {
        Serial.println("[BOOT] IWDG init failed — ESTOP");
        EnterEstop(FaultType::IWDG_PREV_BOOT);
        return false;
    }

    Serial.println("[SAFETY] Init OK");
    return true;
}

void Safety_Update() {
    uint32_t now = HAL_GetTick();

    if (g_rt.active_fault == FaultType::IWDG_PREV_BOOT) {
        HandleFault(FaultType::IWDG_PREV_BOOT, now);
    } else {
        FaultType f = DetectFault(now);
        HandleFault(f, now);
    }

    IWDG_Kick();
}

bool Safety_IsEstop() {
    return g_rt.state == SystemState::ESTOP;
}

const char* Safety_GetFaultName() {
    return FaultName(g_rt.active_fault);
}

// Called from main loop every time HX711 reads successfully
void Safety_NotifyHX711Ok() {
    g_rt.last_hx711_ok_ms = HAL_GetTick();
}
