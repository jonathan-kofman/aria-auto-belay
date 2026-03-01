/**
 * ARIA — Wiring Verification Header
 * wiring_verify.h
 *
 * Call verifyWiringAndSensors() from setup() before initFOC().
 * Returns true = all pass. False = halt.
 */
#pragma once
bool verifyWiringAndSensors();
