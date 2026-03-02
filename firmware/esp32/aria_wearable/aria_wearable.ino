/**
 * ARIA Wearable Voice Unit Firmware
 * ============================================================
 * Hardware : Nordic nRF52810 + PDM microphone + CR2032
 * Clips to : harness belay loop
 * Function : Capture PDM audio, stream raw 16kHz frames over
 *            BLE to the base ESP32-S3.
 *            All wake-word inference runs at the base.
 *            This device is intentionally dumb — no ML, no DSP.
 *
 * Board    : Adafruit nRF52 BSP
 * Power    : CR2032 ~220mAh. Active draw ~4-5mA → ~40-50hr life
 *            (~20-50 climbing sessions per battery)
 *
 * BLE UUIDs must match aria_esp32_firmware.ino exactly.
 * ============================================================
 */

#include <bluefruit.h>
#include <PDM.h>

// ── Config ────────────────────────────────────────────────────
#define SAMPLE_RATE       16000
#define FRAME_SAMPLES     160      // 10ms per BLE frame
#define FRAME_BYTES       (FRAME_SAMPLES * 2)   // int16 = 320 bytes
#define IDLE_TIMEOUT_MS   (10UL * 60UL * 1000UL)

// Pins — adjust for your nRF52810 module
#define PIN_PDM_CLK       11
#define PIN_PDM_DATA      12
#define PIN_LED           13
#define PIN_BATT_ADC      A0

// ── BLE UUIDs (must match ESP32 side) ─────────────────────────
#define WEARABLE_SVC_UUID   "AB000001-1234-1234-1234-ABCDEF012345"
#define AUDIO_CHAR_UUID     "AB000002-1234-1234-1234-ABCDEF012345"
#define STATUS_CHAR_UUID    "AB000003-1234-1234-1234-ABCDEF012345"

BLEService        wearableSvc(WEARABLE_SVC_UUID);
BLECharacteristic audioChar(AUDIO_CHAR_UUID);
BLECharacteristic statusChar(STATUS_CHAR_UUID);

// ── Audio buffers ─────────────────────────────────────────────
static int16_t  pdmBuf[FRAME_SAMPLES * 2];
static int16_t  txFrame[FRAME_SAMPLES];
static volatile bool frameReady = false;

// ── State ─────────────────────────────────────────────────────
static bool     connected      = false;
static uint32_t lastActivityMs = 0;
static uint8_t  batteryPct     = 100;

// ─────────────────────────────────────────────────────────────
// PDM callback — ISR context
// ─────────────────────────────────────────────────────────────
void onPDMData() {
  int got = PDM.read(pdmBuf, sizeof(pdmBuf));
  if (got == (int)sizeof(pdmBuf) && !frameReady) {
    memcpy(txFrame, pdmBuf, FRAME_BYTES);
    frameReady = true;
  }
}

// ─────────────────────────────────────────────────────────────
// BLE callbacks
// ─────────────────────────────────────────────────────────────
void onConnect(uint16_t handle) {
  connected      = true;
  lastActivityMs = millis();
  digitalWrite(PIN_LED, HIGH);
  PDM.setBufferSize(sizeof(pdmBuf));
  PDM.onReceive(onPDMData);
  PDM.begin(1, SAMPLE_RATE);
}

void onDisconnect(uint16_t handle, uint8_t reason) {
  connected  = false;
  frameReady = false;
  digitalWrite(PIN_LED, LOW);
  PDM.end();
  Bluefruit.Advertising.start(0);
}

// ─────────────────────────────────────────────────────────────
// CR2032 estimate: 3.0V=100%, 2.0V=0%
// Assumes voltage divider /2, 3.3V ADC reference
// ─────────────────────────────────────────────────────────────
uint8_t readBattery() {
  float v = (analogRead(PIN_BATT_ADC) / 1023.0f) * 3.3f * 2.0f;
  if (v >= 3.0f) return 100;
  if (v <= 2.0f) return 0;
  return (uint8_t)((v - 2.0f) * 100.0f);
}

// ─────────────────────────────────────────────────────────────
// Setup
// ─────────────────────────────────────────────────────────────
void setup() {
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  analogReadResolution(10);

  Bluefruit.begin();
  Bluefruit.setTxPower(4);
  Bluefruit.setName("ARIA-VOICE");
  Bluefruit.Periph.setConnectCallback(onConnect);
  Bluefruit.Periph.setDisconnectCallback(onDisconnect);

  wearableSvc.begin();

  // Audio: notify only, 320 bytes per frame
  audioChar.setProperties(CHR_PROPS_NOTIFY);
  audioChar.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  audioChar.setMaxLen(FRAME_BYTES);
  audioChar.begin();

  // Status: read + notify, [battery%, connected]
  statusChar.setProperties(CHR_PROPS_READ | CHR_PROPS_NOTIFY);
  statusChar.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  statusChar.setMaxLen(2);
  statusChar.begin();
  uint8_t init[2] = {100, 0};
  statusChar.write(init, 2);

  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(wearableSvc);
  Bluefruit.Advertising.addName();
  Bluefruit.Advertising.setInterval(32, 244);
  Bluefruit.Advertising.setFastTimeout(30);
  Bluefruit.Advertising.start(0);
}

// ─────────────────────────────────────────────────────────────
// Loop
// ─────────────────────────────────────────────────────────────
void loop() {
  if (!connected) {
    // Idle timeout — drop to slow advertising to save battery
    if (millis() - lastActivityMs > IDLE_TIMEOUT_MS) {
      Bluefruit.Advertising.setInterval(1600, 1600);
    }
    return;
  }

  lastActivityMs = millis();

  // Send audio frame when ready
  if (frameReady) {
    frameReady = false;
    if (audioChar.notifyEnabled()) {
      audioChar.notify((uint8_t*)txFrame, FRAME_BYTES);
    }
  }

  // Update battery status every 10s
  static uint32_t lastStatusMs = 0;
  if (millis() - lastStatusMs > 10000) {
    lastStatusMs = millis();
    batteryPct = readBattery();
    uint8_t status[2] = {batteryPct, 1};
    statusChar.write(status, 2);
    if (statusChar.notifyEnabled()) {
      statusChar.notify(status, 2);
    }
    // batteryPct < 10 — base unit will show "REPLACE WEARABLE BATTERY" on OLED
  }

  yield();
}
