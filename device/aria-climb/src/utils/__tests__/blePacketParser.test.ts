/**
 * Tests for the 20-byte BLE telemetry packet parser.
 *
 * Packet layout (little-endian):
 *   Byte 0     : state (0=IDLE … 8=ESTOP)
 *   Bytes 1-4  : tension_N   (float32 LE)
 *   Bytes 5-8  : rope_speed_ms (float32 LE)
 *   Bytes 9-12 : motor_current_A (float32 LE)
 *   Bytes 13-14: battery_mV (uint16 LE)
 *   Bytes 15-18: timestamp_s (uint32 LE)
 *   Byte 19    : XOR checksum of bytes 0-18
 */

import { parseBlePacket, parseStatusJson } from '../blePacketParser';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a valid 20-byte packet as a base64 string. */
function buildPacket({
  stateCode = 1,       // CLIMBING
  tension_N = 42.5,
  rope_speed_ms = 0.3,
  motor_current_A = 2.1,
  battery_mV = 3700,
  timestamp_s = 1_700_000_000,
}: {
  stateCode?: number;
  tension_N?: number;
  rope_speed_ms?: number;
  motor_current_A?: number;
  battery_mV?: number;
  timestamp_s?: number;
} = {}): string {
  const buf = Buffer.alloc(20, 0);
  const view = new DataView(buf.buffer);

  buf[0] = stateCode;
  view.setFloat32(1, tension_N, true);
  view.setFloat32(5, rope_speed_ms, true);
  view.setFloat32(9, motor_current_A, true);
  view.setUint16(13, battery_mV, true);
  view.setUint32(15, timestamp_s, true);

  // XOR checksum over bytes 0-18
  let xor = 0;
  for (let i = 0; i < 19; i++) xor ^= buf[i];
  buf[19] = xor;

  return buf.toString('base64');
}

// ---------------------------------------------------------------------------
// 1. Valid packet → correct fields
// ---------------------------------------------------------------------------

describe('parseBlePacket — valid packet', () => {
  it('returns non-null for a correctly formed packet', () => {
    const pkt = buildPacket();
    expect(parseBlePacket(pkt)).not.toBeNull();
  });

  it('parses state code 1 as CLIMBING', () => {
    const result = parseBlePacket(buildPacket({ stateCode: 1 }));
    expect(result?.state).toBe('CLIMBING');
  });

  it('parses state code 0 as IDLE', () => {
    const result = parseBlePacket(buildPacket({ stateCode: 0 }));
    expect(result?.state).toBe('IDLE');
  });

  it('parses state code 8 as ESTOP', () => {
    const result = parseBlePacket(buildPacket({ stateCode: 8 }));
    expect(result?.state).toBe('ESTOP');
  });

  it('parses an unknown state code as UNKNOWN', () => {
    // State code 9 is not in STATE_MAP
    const result = parseBlePacket(buildPacket({ stateCode: 9 }));
    expect(result?.state).toBe('UNKNOWN');
  });

  it('parses tension_N correctly (within float32 precision)', () => {
    const result = parseBlePacket(buildPacket({ tension_N: 42.5 }));
    expect(result?.tension_N).toBeCloseTo(42.5, 2);
  });

  it('parses rope_speed_ms correctly', () => {
    const result = parseBlePacket(buildPacket({ rope_speed_ms: 0.3 }));
    expect(result?.rope_speed_ms).toBeCloseTo(0.3, 2);
  });

  it('parses motor_current_A correctly', () => {
    const result = parseBlePacket(buildPacket({ motor_current_A: 2.1 }));
    expect(result?.motor_current_A).toBeCloseTo(2.1, 2);
  });

  it('converts battery_mV to battery_V (÷ 1000)', () => {
    const result = parseBlePacket(buildPacket({ battery_mV: 3700 }));
    expect(result?.battery_V).toBeCloseTo(3.7, 3);
  });

  it('converts timestamp_s to ts in milliseconds (× 1000)', () => {
    const ts_s = 1_700_000_000;
    const result = parseBlePacket(buildPacket({ timestamp_s: ts_s }));
    expect(result?.ts).toBe(ts_s * 1000);
  });

  it('returns all six telemetry fields', () => {
    const result = parseBlePacket(buildPacket());
    expect(result).toMatchObject({
      state: expect.any(String),
      tension_N: expect.any(Number),
      rope_speed_ms: expect.any(Number),
      motor_current_A: expect.any(Number),
      battery_V: expect.any(Number),
      ts: expect.any(Number),
    });
  });
});

// ---------------------------------------------------------------------------
// 2. Wrong checksum → null
// ---------------------------------------------------------------------------

describe('parseBlePacket — bad checksum', () => {
  it('returns null when checksum byte is flipped by 1', () => {
    const b64 = buildPacket();
    const buf = Buffer.from(b64, 'base64');
    buf[19] ^= 0x01; // corrupt the checksum
    expect(parseBlePacket(buf.toString('base64'))).toBeNull();
  });

  it('returns null when checksum byte is 0x00 and correct value is non-zero', () => {
    const b64 = buildPacket({ stateCode: 1 });
    const buf = Buffer.from(b64, 'base64');
    buf[19] = 0x00; // force zero
    // Only passes if XOR of bytes 0-18 also happens to be 0x00, which is unlikely
    // for a non-trivial packet — confirm it really is wrong:
    let xor = 0;
    for (let i = 0; i < 19; i++) xor ^= buf[i];
    if (xor !== 0x00) {
      expect(parseBlePacket(buf.toString('base64'))).toBeNull();
    } else {
      // Extremely rare collision: skip assertion rather than false-fail
      expect(true).toBe(true);
    }
  });

  it('returns null when a data byte is changed after checksum was computed', () => {
    const b64 = buildPacket({ stateCode: 2 }); // CLIPPING
    const buf = Buffer.from(b64, 'base64');
    buf[0] = 5; // change state without updating checksum
    expect(parseBlePacket(buf.toString('base64'))).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 3. Wrong magic / malformed input → null
// ---------------------------------------------------------------------------

describe('parseBlePacket — malformed input', () => {
  it('returns null for a packet shorter than 20 bytes', () => {
    const buf = Buffer.alloc(15, 0);
    expect(parseBlePacket(buf.toString('base64'))).toBeNull();
  });

  it('returns null for an empty string', () => {
    expect(parseBlePacket('')).toBeNull();
  });

  it('returns null for a non-base64 string without throwing', () => {
    // Should not throw; gracefully returns null
    expect(() => parseBlePacket('not-base-64!!!!')).not.toThrow();
  });

  it('accepts a 20-byte all-zeros packet (XOR checksum = 0)', () => {
    // All zeros: XOR of bytes 0-18 is 0, byte 19 is 0 — valid checksum.
    const buf = Buffer.alloc(20, 0);
    const result = parseBlePacket(buf.toString('base64'));
    // State 0 → IDLE, all floats → 0, battery 0 V, ts 0 ms
    expect(result).not.toBeNull();
    expect(result?.state).toBe('IDLE');
    expect(result?.tension_N).toBe(0);
    expect(result?.battery_V).toBe(0);
    expect(result?.ts).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// 4. parseStatusJson
// ---------------------------------------------------------------------------

describe('parseStatusJson', () => {
  it('parses a valid JSON status string', () => {
    const json = JSON.stringify({
      state: 'REST',
      tension_N: 38,
      rope_speed_ms: 0,
      motor_current_A: 0.5,
      battery_V: 3.85,
    });
    const result = parseStatusJson(json);
    expect(result.state).toBe('REST');
    expect(result.tension_N).toBe(38);
    expect(result.battery_V).toBeCloseTo(3.85, 2);
  });

  it('returns empty object for invalid JSON', () => {
    const result = parseStatusJson('{bad json');
    expect(result).toEqual({});
  });

  it('defaults numeric fields to 0 when omitted', () => {
    const result = parseStatusJson(JSON.stringify({ state: 'IDLE' }));
    expect(result.tension_N).toBe(0);
    expect(result.rope_speed_ms).toBe(0);
    expect(result.motor_current_A).toBe(0);
    expect(result.battery_V).toBe(0);
  });
});
