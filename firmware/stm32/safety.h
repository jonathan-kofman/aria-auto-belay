/**
 * ARIA — Safety Layer
 * safety.h — Watchdog + Fault Recovery Header
 *
 * Include this in aria_main.cpp
 */

#pragma once
#include <Arduino.h>

// ─────────────────────────────────────────────
// PUBLIC API — call these from main firmware
// ─────────────────────────────────────────────

/**
 * Power-safety boot sequence:
 *
 *  1. Safety_BootBegin()        → engage mechanical brake GPIO HIGH.
 *  2. HX711 / load cell init    → on success, call Safety_BootMarkHX711Ok().
 *  3. Encoder init              → on success, call Safety_BootMarkEncoderOk().
 *  4. UART init (ESP32 link)    → on success, call Safety_BootMarkUartOk().
 *  5. Motor + FOC init          → on success, call Safety_BootMarkMotorOk().
 *  6. First heartbeat to ESP32  → call uart_tx() from aria_main.cpp.
 *  7. Safety_BootComplete()     → if all flags set, release brake; otherwise ESTOP.
 *
 * If any step never calls its Safety_BootMark* function, the system remains
 * in a faulted boot state with the brake engaged.
 */
void Safety_BootBegin();
void Safety_BootMarkHX711Ok();
void Safety_BootMarkEncoderOk();
void Safety_BootMarkUartOk();
void Safety_BootMarkMotorOk();
void Safety_BootComplete();

/**
 * Call once in setup() after all peripherals initialized
 * (and after Safety_BootComplete has been called).
 *
 * Detects prior IWDG reset, initializes watchdog timer.
 * Returns false if IWDG init failed (system should halt).
 */
bool Safety_Init();

/**
 * Call every loop iteration — before state machine logic.
 * Detects faults, attempts recovery, kicks watchdog.
 * If fault is unrecoverable, motor is disabled and ESTOP latched.
 */
void Safety_Update();

/**
 * Returns true if system is in ESTOP state.
 * Check this before any motor commands.
 */
bool Safety_IsEstop();

/**
 * Returns name string of active fault (or "NONE").
 */
const char* Safety_GetFaultName();

/**
 * Update this timestamp whenever a valid ESP32 UART packet arrives.
 * Safety_Update() uses it to detect ESP32 timeout.
 */
extern volatile uint32_t g_lastEsp32RxMs;
