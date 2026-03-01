/**
 * ARIA — ESP32-S3 Intelligence Layer Firmware
 * aria_esp32_firmware.ino
 *
 * Board: Seeed XIAO ESP32-S3 Sense
 * Framework: Arduino (ESP-IDF)
 *
 * FreeRTOS Tasks:
 *   Task 1 (Core 0): Voice — Edge Impulse wake word detection
 *   Task 2 (Core 0): CV   — OV2640 camera, climber tracking, clip detection
 *   Task 3 (Core 1): UART — STM32 communication + ping/ack handler
 *
 * UART Protocol to STM32:
 *   Send voice: V:<cmd_id>:<confidence>\n
 *   Send CV:    C:<clip_conf>:<height_m>:<detected>\n
 *   Receive:    S:<state>:<tension>:<rope_pos>:<motor_mode>\n
 *
 * Wiring:
 *   GPIO43 (TX) → STM32 PA3 (UART2 RX)
 *   GPIO44 (RX) ← STM32 PA2 (UART2 TX)
 *   GND → GND (do NOT connect 3.3V)
 *
 * Setup:
 *   1. Install Edge Impulse library (see docs/edge_impulse_setup.md)
 *   2. Uncomment #include for your generated library
 *   3. Uncomment and implement the inference loop in voice_task()
 */

#include <Arduino.h>
#include <HardwareSerial.h>
#include "esp_camera.h"

// Uncomment after generating your Edge Impulse library:
// #include "aria-wake-word_inferencing.h"

// ─────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────

#define UART_BAUD            115200
#define STM32_UART_TX        43
#define STM32_UART_RX        44
#define VOICE_CONF_MIN       0.85f
#define CLIP_CONF_MIN        0.75f

// Camera pins — XIAO ESP32-S3 Sense OV2640
#define PWDN_GPIO_NUM   -1
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM   10
#define SIOD_GPIO_NUM   40
#define SIOC_GPIO_NUM   39
#define Y9_GPIO_NUM     48
#define Y8_GPIO_NUM     11
#define Y7_GPIO_NUM     12
#define Y6_GPIO_NUM     14
#define Y5_GPIO_NUM     16
#define Y4_GPIO_NUM     18
#define Y3_GPIO_NUM     17
#define Y2_GPIO_NUM     15
#define VSYNC_GPIO_NUM  38
#define HREF_GPIO_NUM   47
#define PCLK_GPIO_NUM   13

// Ping/ack protocol (matches wiring_verify.cpp)
#define PKT0       0xAA
#define PKT1       0x55
#define TYPE_PING  0x01
#define TYPE_ACK   0x81

// ─────────────────────────────────────────────
// VOICE COMMAND IDS (must match STM32 firmware)
// ─────────────────────────────────────────────

typedef enum : uint8_t {
    CMD_NONE=0, CMD_TAKE=1, CMD_SLACK=2, CMD_LOWER=3,
    CMD_UP=4, CMD_WATCH_ME=5, CMD_REST=6, CMD_CLIMBING=7
} VoiceCmd;

struct LabelMap { const char* label; VoiceCmd cmd; };
const LabelMap LABEL_MAP[] = {
    {"take",     CMD_TAKE},
    {"slack",    CMD_SLACK},
    {"lower",    CMD_LOWER},
    {"up",       CMD_UP},
    {"watch_me", CMD_WATCH_ME},
    {"rest",     CMD_REST},
    {"climbing", CMD_CLIMBING},
};
const int LABEL_MAP_LEN = sizeof(LABEL_MAP)/sizeof(LABEL_MAP[0]);

// ─────────────────────────────────────────────
// GLOBALS
// ─────────────────────────────────────────────

HardwareSerial STM32Serial(1);

// STM32 state
int   g_stm_state    = 0;
float g_stm_tension  = 0.0f;
float g_stm_rope_pos = 0.0f;
int   g_stm_motor    = 0;

// CV state
float g_cv_height    = 0.0f;
float g_cv_clip_conf = 0.0f;
bool  g_cv_detected  = false;
int   g_prev_cy      = -1;

// UART RX buffer
#define UART_BUF_SIZE 64
char    g_ubuf[UART_BUF_SIZE];
uint8_t g_uidx = 0;

// Task handles
TaskHandle_t h_voice = NULL;
TaskHandle_t h_cv    = NULL;
TaskHandle_t h_uart  = NULL;

// ─────────────────────────────────────────────
// UART TX
// ─────────────────────────────────────────────

void uart_send_voice(VoiceCmd cmd, float conf) {
    char buf[32];
    snprintf(buf, sizeof(buf), "V:%d:%.2f\n", (int)cmd, conf);
    STM32Serial.print(buf);
    Serial.printf("[VOICE→STM32] %s", buf);
}

void uart_send_cv(float clip, float height, bool det) {
    char buf[48];
    snprintf(buf, sizeof(buf), "C:%.2f:%.1f:%d\n", clip, height, (int)det);
    STM32Serial.print(buf);
}

// ─────────────────────────────────────────────
// UART RX PARSER (from STM32 + ping/ack handler)
// ─────────────────────────────────────────────

uint8_t pkt_cs(const uint8_t* b, size_t n) {
    uint8_t x=0; for(size_t i=0;i<n;i++) x^=b[i]; return x;
}

void uart_send_ack(uint8_t seq) {
    uint8_t pkt[5] = {PKT0, PKT1, TYPE_ACK, seq, 0};
    pkt[4] = pkt_cs(pkt, 4);
    STM32Serial.write(pkt, 5);
}

void uart_parse(const char* p) {
    if (p[0]=='S') {
        sscanf(p+2, "%d:%f:%f:%d",
               &g_stm_state, &g_stm_tension,
               &g_stm_rope_pos, &g_stm_motor);
    }
}

void uart_handle_binary(uint8_t c) {
    // Detect ping packet header in binary stream
    static uint8_t bpkt[5];
    static uint8_t bidx = 0;

    if (bidx==0 && c!=PKT0) return;
    if (bidx==1 && c!=PKT1) { bidx=0; return; }
    bpkt[bidx++] = c;
    if (bidx==5) {
        bidx = 0;
        uint8_t cs = pkt_cs(bpkt, 4);
        if (bpkt[2]==TYPE_PING && bpkt[4]==cs) {
            uart_send_ack(bpkt[3]);
            Serial.println("[UART] Ping received — ACK sent");
        }
    }
}

// ─────────────────────────────────────────────
// CAMERA INIT
// ─────────────────────────────────────────────

bool camera_init() {
    camera_config_t cfg;
    cfg.ledc_channel = LEDC_CHANNEL_0;
    cfg.ledc_timer   = LEDC_TIMER_0;
    cfg.pin_d0=Y2_GPIO_NUM; cfg.pin_d1=Y3_GPIO_NUM;
    cfg.pin_d2=Y4_GPIO_NUM; cfg.pin_d3=Y5_GPIO_NUM;
    cfg.pin_d4=Y6_GPIO_NUM; cfg.pin_d5=Y7_GPIO_NUM;
    cfg.pin_d6=Y8_GPIO_NUM; cfg.pin_d7=Y9_GPIO_NUM;
    cfg.pin_xclk=XCLK_GPIO_NUM; cfg.pin_pclk=PCLK_GPIO_NUM;
    cfg.pin_vsync=VSYNC_GPIO_NUM; cfg.pin_href=HREF_GPIO_NUM;
    cfg.pin_sccb_sda=SIOD_GPIO_NUM; cfg.pin_sccb_scl=SIOC_GPIO_NUM;
    cfg.pin_pwdn=PWDN_GPIO_NUM; cfg.pin_reset=RESET_GPIO_NUM;
    cfg.xclk_freq_hz  = 20000000;
    cfg.pixel_format  = PIXFORMAT_GRAYSCALE;
    cfg.frame_size    = FRAMESIZE_QVGA;
    cfg.fb_count      = 1;
    cfg.grab_mode     = CAMERA_GRAB_LATEST;
    esp_err_t err = esp_camera_init(&cfg);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed: 0x%x\n", err);
        return false;
    }
    Serial.println("Camera OK");
    return true;
}

// ─────────────────────────────────────────────
// CV — OPTICAL FLOW CLIMBER TRACKER
// ─────────────────────────────────────────────

void cv_process(camera_fb_t* fb) {
    if (!fb) return;
    uint8_t* px = fb->buf;
    int w=fb->width, h=fb->height;
    long sy=0, cnt=0;
    uint8_t thr=80;  // tune for your gym lighting

    for(int y=0;y<h;y++) for(int x=0;x<w;x++) {
        if(px[y*w+x]<thr) { sy+=y; cnt++; }
    }

    if(cnt>500) {
        g_cv_detected = true;
        int cy = (int)(sy/cnt);
        const float WALL_H = 15.0f;  // tune to actual wall height
        g_cv_height = WALL_H*(1.0f-(float)cy/(float)h);

        if(g_prev_cy>0) {
            int dy = g_prev_cy - cy;
            if(dy==0 && g_cv_height>1.5f)
                g_cv_clip_conf = min(g_cv_clip_conf+0.15f, 1.0f);
            else
                g_cv_clip_conf = max(g_cv_clip_conf-0.1f, 0.0f);
        }
        g_prev_cy = cy;
    } else {
        g_cv_detected  = false;
        g_cv_clip_conf = max(g_cv_clip_conf-0.2f, 0.0f);
        g_prev_cy      = -1;
    }
}

// ─────────────────────────────────────────────
// FREERTOS TASKS
// ─────────────────────────────────────────────

// Task 1: Voice (Core 0)
void voice_task(void* p) {
    Serial.println("[TASK] Voice started");
    // ── PLACEHOLDER ──
    // Replace this block with Edge Impulse inference loop
    // after running: python3 tools/aria_collect_audio.py
    // and training your model at studio.edgeimpulse.com
    // See docs/edge_impulse_setup.md for full instructions
    //
    // Example inference loop:
    // while(true) {
    //   if (microphone_inference_record()) {
    //     signal_t sig;
    //     microphone_inference_signal_get_data(0,0,&sig);
    //     ei_impulse_result_t result;
    //     run_classifier_continuous(&sig, &result, false);
    //     float best=0; int bidx=-1;
    //     for(int i=0;i<EI_CLASSIFIER_LABEL_COUNT;i++) {
    //       if(result.classification[i].value>best) {
    //         best=result.classification[i].value; bidx=i;
    //       }
    //     }
    //     if(best>=VOICE_CONF_MIN && bidx>=0) {
    //       const char* lbl=ei_classifier_inferencing_categories[bidx];
    //       for(int j=0;j<LABEL_MAP_LEN;j++) {
    //         if(strcmp(lbl,LABEL_MAP[j].label)==0) {
    //           uart_send_voice(LABEL_MAP[j].cmd, best);
    //         }
    //       }
    //     }
    //   }
    //   vTaskDelay(pdMS_TO_TICKS(10));
    // }
    while(true) vTaskDelay(pdMS_TO_TICKS(50));
}

// Task 2: CV (Core 0)
void cv_task(void* p) {
    Serial.println("[TASK] CV started");
    if (!camera_init()) { vTaskDelete(NULL); return; }

    while(true) {
        camera_fb_t* fb = esp_camera_fb_get();
        if(fb) {
            cv_process(fb);
            esp_camera_fb_return(fb);
            uart_send_cv(g_cv_clip_conf, g_cv_height, g_cv_detected);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

// Task 3: UART (Core 1)
void uart_task(void* p) {
    Serial.println("[TASK] UART started");
    while(true) {
        while(STM32Serial.available()) {
            uint8_t c = (uint8_t)STM32Serial.read();

            // Try binary ping detection first
            if(c==PKT0) {
                uart_handle_binary(c);
                continue;
            }
            // Otherwise ASCII line protocol
            if((char)c=='\n') {
                g_ubuf[g_uidx]='\0';
                uart_parse(g_ubuf);
                g_uidx=0;
            } else if(g_uidx<UART_BUF_SIZE-1) {
                g_ubuf[g_uidx++]=(char)c;
                // also feed binary handler for mid-stream detection
                uart_handle_binary(c);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

// ─────────────────────────────────────────────
// SETUP & LOOP
// ─────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("ARIA ESP32-S3 Intelligence Layer v0.2");

    STM32Serial.begin(UART_BAUD, SERIAL_8N1, STM32_UART_RX, STM32_UART_TX);
    Serial.println("UART to STM32 ready");

    // Launch FreeRTOS tasks
    xTaskCreatePinnedToCore(voice_task, "voice", 8192, NULL, 2, &h_voice, 0);
    xTaskCreatePinnedToCore(cv_task,   "cv",    8192, NULL, 1, &h_cv,    0);
    xTaskCreatePinnedToCore(uart_task, "uart",  4096, NULL, 3, &h_uart,  1);

    Serial.println("ARIA ESP32 ready");
}

void loop() {
    static uint32_t last=0;
    if(millis()-last>2000) {
        last=millis();
        Serial.printf("[STATUS] STM32 state=%d tension=%.1fN | CV h=%.1fm clip=%.2f det=%d\n",
                      g_stm_state, g_stm_tension,
                      g_cv_height, g_cv_clip_conf, (int)g_cv_detected);
    }
    delay(100);
}
