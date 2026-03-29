/**
 * Parse a 20-byte binary BLE telemetry packet from the ARIA ESP32.
 *
 * Packet layout (little-endian):
 *   Byte 0     : state  (mirrors STM32 ARIAState enum:
 *                  0=IDLE 1=CLIMBING 2=CLIPPING 3=TAKE 4=REST
 *                  5=LOWER 6=WATCH_ME 7=UP 8=ESTOP)
 *   Bytes 1-4  : tension_N   (float32)
 *   Bytes 5-8  : rope_speed_ms (float32, positive=paying out)
 *   Bytes 9-12 : motor_current_A (float32)
 *   Bytes 13-14: battery_mV (uint16, mV)
 *   Bytes 15-18: timestamp_s (uint32, seconds since epoch)
 *   Byte 19    : checksum (XOR of bytes 0-18)
 */

import type { ARIAState, ARIATelemetry } from '../types/aria';

const STATE_MAP: Record<number, ARIAState> = {
  0: 'IDLE',
  1: 'CLIMBING',
  2: 'CLIPPING',
  3: 'TAKE',
  4: 'REST',
  5: 'LOWER',
  6: 'WATCH_ME',
  7: 'UP',
  8: 'ESTOP',
};

function xorChecksum(bytes: Uint8Array, len: number): number {
  let x = 0;
  for (let i = 0; i < len; i++) x ^= bytes[i];
  return x;
}

/**
 * Parse a base64-encoded BLE notify value into ARIATelemetry.
 * Returns null if the packet is malformed or checksum fails.
 */
export function parseBlePacket(base64: string): ARIATelemetry | null {
  try {
    const raw = Buffer.from(base64, 'base64');
    if (raw.length < 20) return null;

    const bytes = new Uint8Array(raw);
    const expected = xorChecksum(bytes, 19);
    if (bytes[19] !== expected) return null;

    const view = new DataView(raw.buffer, raw.byteOffset, raw.byteLength);

    const stateCode = bytes[0];
    const state: ARIAState = STATE_MAP[stateCode] ?? 'UNKNOWN';
    const tension_N = view.getFloat32(1, true);
    const rope_speed_ms = view.getFloat32(5, true);
    const motor_current_A = view.getFloat32(9, true);
    const battery_V = view.getUint16(13, true) / 1000;
    const ts = view.getUint32(15, true) * 1000; // to ms

    return { state, tension_N, rope_speed_ms, motor_current_A, battery_V, ts };
  } catch {
    return null;
  }
}

/**
 * Parse a JSON-encoded status string (from ARIA_CHAR_STATUS).
 * Returns a partial telemetry snapshot; missing fields default to 0.
 */
export function parseStatusJson(json: string): Partial<ARIATelemetry> {
  try {
    const obj = JSON.parse(json);
    return {
      state: (obj.state as ARIAState) ?? 'UNKNOWN',
      tension_N: Number(obj.tension_N ?? 0),
      rope_speed_ms: Number(obj.rope_speed_ms ?? 0),
      motor_current_A: Number(obj.motor_current_A ?? 0),
      battery_V: Number(obj.battery_V ?? 0),
      ts: Date.now(),
    };
  } catch {
    return {};
  }
}
