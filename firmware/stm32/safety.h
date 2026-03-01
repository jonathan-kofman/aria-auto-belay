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
 * Call once in setup() after all peripherals initialized.
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
