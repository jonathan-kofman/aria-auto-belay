/**
 * ARIA — ESP32-S3 Intelligence Layer Firmware
 * aria_esp32_firmware.ino
 *
 * Board:      Seeed XIAO ESP32-S3 Sense
 * Version:    0.3.0
 *
 * NEW in 0.3:
 *   BLE provisioning (first boot only, saves to NVS)
 *   WiFi connect from NVS credentials
 *   Firebase Firestore REST heartbeat every 10s
 *   Firebase event push (falls, voice, state changes)
 *   Firebase command polling (gym app → STM32 forwarding)
 *   Anonymous Firebase auth
 *
 * FreeRTOS Tasks:
 *   Core 0 — voice:    Edge Impulse wake word
 *   Core 0 — cv:       OV2640 climber tracking
 *   Core 1 — uart:     STM32 comms + ping/ack
 *   Core 1 — firebase: heartbeat + events + commands
 *
 * UART Protocol (unchanged):
 *   Send voice:    V:<cmd_id>:<confidence>\n
 *   Send CV:       C:<clip_conf>:<height_m>:<detected>\n
 *   Send cmd fwd:  CMD:PAUSE | CMD:RESUME | CMD:LOCKOUT | CMD:RETURN\n
 *   Receive:       S:<state>:<tension>:<rope_pos>:<motor_mode>\n
 *
 * Wiring (unchanged):
 *   GPIO43 TX → STM32 PA3 RX
 *   GPIO44 RX ← STM32 PA2 TX
 *   GND → GND
 *
 * First-time setup:
 *   1. Set FIREBASE_PROJECT_ID + FIREBASE_API_KEY below
 *   2. Flash firmware
 *   3. Open ARIA app → Add Device → scan for ARIA-XXYYZZ
 *   4. App sends WiFi + gym credentials over BLE
 *   5. Device reboots, goes online in Firebase
 *   To re-provision: type "reset" in Serial Monitor
 */

// ─────────────────────────────────────────────
// INCLUDES
// ─────────────────────────────────────────────

#include <Arduino.h>
#include <HardwareSerial.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include "esp_camera.h"

// Uncomment after generating your Edge Impulse library:
// #include "aria-wake-word_inferencing.h"

// ─────────────────────────────────────────────
// CONSTANTS — UART / VOICE
// ─────────────────────────────────────────────

#define UART_BAUD       115200
#define STM32_UART_TX   43
#define STM32_UART_RX   44
#define VOICE_CONF_MIN  0.85f
#define CLIP_CONF_MIN   0.75f

// ─────────────────────────────────────────────
// CONSTANTS — CAMERA PINS (XIAO ESP32-S3 Sense)
// ─────────────────────────────────────────────

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

// ─────────────────────────────────────────────
// CONSTANTS — PING/ACK
// ─────────────────────────────────────────────

#define PKT0       0xAA
#define PKT1       0x55
#define TYPE_PING  0x01
#define TYPE_ACK   0x81

// ─────────────────────────────────────────────
// CONSTANTS — BLE PROVISIONING
// Must match src/services/ble/bleProvisioning.ts
// ─────────────────────────────────────────────

#define PROVISIONING_SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define WIFI_CHAR_UUID            "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define GYM_CHAR_UUID             "beb5483f-36e1-4688-b7f5-ea07361b26a8"
#define STATUS_CHAR_UUID          "beb54840-36e1-4688-b7f5-ea07361b26a8"

// ─────────────────────────────────────────────
// CONSTANTS — FIREBASE
// Get from: Firebase Console → Project Settings
// ─────────────────────────────────────────────

#define FIREBASE_PROJECT_ID  "your-project-id"
#define FIREBASE_API_KEY     "your-web-api-key"
#define FIREBASE_BASE_URL    "https://firestore.googleapis.com/v1/projects/" \
                             FIREBASE_PROJECT_ID "/databases/(default)/documents"

#define HEARTBEAT_INTERVAL_MS  10000
#define CMD_POLL_INTERVAL_MS    5000
#define FALL_TENSION_DELTA      15.0f

// ─────────────────────────────────────────────
// VOICE COMMAND IDS
// ─────────────────────────────────────────────

typedef enum : uint8_t {
    CMD_NONE=0, CMD_TAKE=1, CMD_SLACK=2, CMD_LOWER=3,
    CMD_UP=4, CMD_WATCH_ME=5, CMD_REST=6, CMD_CLIMBING=7
} VoiceCmd;

struct LabelMap { const char* label; VoiceCmd cmd; };
const LabelMap LABEL_MAP[] = {
    {"take",CMD_TAKE},{"slack",CMD_SLACK},{"lower",CMD_LOWER},{"up",CMD_UP},
    {"watch_me",CMD_WATCH_ME},{"rest",CMD_REST},{"climbing",CMD_CLIMBING},
};
const int LABEL_MAP_LEN = sizeof(LABEL_MAP)/sizeof(LABEL_MAP[0]);

// ─────────────────────────────────────────────
// STATE MAP
// ─────────────────────────────────────────────

const char* STATE_STRINGS[] = {
    "IDLE","CLIMBING","CLIPPING","TAKE","REST",
    "LOWER","WATCH_ME","UP","FAULT","LOCKOUT","MAINTENANCE"
};
const int STATE_COUNT = sizeof(STATE_STRINGS)/sizeof(STATE_STRINGS[0]);

const char* state_to_string(int s) {
    return (s>=0 && s<STATE_COUNT) ? STATE_STRINGS[s] : "IDLE";
}

// ─────────────────────────────────────────────
// GLOBALS — STM32 STATE
// ─────────────────────────────────────────────

volatile int   g_stm_state    = 0;
volatile float g_stm_tension  = 0.0f;
volatile float g_stm_rope_pos = 0.0f;
volatile int   g_stm_motor    = 0;

// ─────────────────────────────────────────────
// GLOBALS — CV STATE
// ─────────────────────────────────────────────

volatile float g_cv_height    = 0.0f;
volatile float g_cv_clip_conf = 0.0f;
volatile bool  g_cv_detected  = false;
int            g_prev_cy      = -1;

// ─────────────────────────────────────────────
// GLOBALS — UART
// ─────────────────────────────────────────────

#define UART_BUF_SIZE 64
char    g_ubuf[UART_BUF_SIZE];
uint8_t g_uidx = 0;
HardwareSerial STM32Serial(1);

// ─────────────────────────────────────────────
// GLOBALS — FIREBASE / WIFI
// ─────────────────────────────────────────────

Preferences prefs;
String      g_gym_id         = "";
String      g_device_id      = "";
String      g_firebase_token = "";
bool        g_wifi_connected = false;
uint32_t    g_uptime_start   = 0;
uint32_t    g_total_falls    = 0;
uint32_t    g_cycle_count    = 0;

// ─────────────────────────────────────────────
// GLOBALS — BLE
// ─────────────────────────────────────────────

BLECharacteristic* g_status_char = nullptr;

struct ProvisioningData {
    String ssid, password, gymId, deviceId;
    bool wifiReceived = false;
    bool gymReceived  = false;
} g_prov;

// ─────────────────────────────────────────────
// GLOBALS — TASK HANDLES
// ─────────────────────────────────────────────

TaskHandle_t h_voice=NULL, h_cv=NULL, h_uart=NULL, h_firebase=NULL;

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
// UART RX + PING/ACK
// ─────────────────────────────────────────────

uint8_t pkt_cs(const uint8_t* b, size_t n) {
    uint8_t x=0; for(size_t i=0;i<n;i++) x^=b[i]; return x;
}

void uart_send_ack(uint8_t seq) {
    uint8_t pkt[5]={PKT0,PKT1,TYPE_ACK,seq,0};
    pkt[4]=pkt_cs(pkt,4);
    STM32Serial.write(pkt,5);
}

void uart_parse(const char* p) {
    if(p[0]=='S')
        sscanf(p+2,"%d:%f:%f:%d",
               (int*)&g_stm_state,(float*)&g_stm_tension,
               (float*)&g_stm_rope_pos,(int*)&g_stm_motor);
}

void uart_handle_binary(uint8_t c) {
    static uint8_t bpkt[5]; static uint8_t bidx=0;
    if(bidx==0 && c!=PKT0) return;
    if(bidx==1 && c!=PKT1){bidx=0;return;}
    bpkt[bidx++]=c;
    if(bidx==5){
        bidx=0;
        if(bpkt[2]==TYPE_PING && bpkt[4]==pkt_cs(bpkt,4)){
            uart_send_ack(bpkt[3]);
            Serial.println("[UART] Ping → ACK");
        }
    }
}

// ─────────────────────────────────────────────
// CAMERA INIT
// ─────────────────────────────────────────────

bool camera_init() {
    camera_config_t cfg;
    cfg.ledc_channel=LEDC_CHANNEL_0; cfg.ledc_timer=LEDC_TIMER_0;
    cfg.pin_d0=Y2_GPIO_NUM; cfg.pin_d1=Y3_GPIO_NUM; cfg.pin_d2=Y4_GPIO_NUM;
    cfg.pin_d3=Y5_GPIO_NUM; cfg.pin_d4=Y6_GPIO_NUM; cfg.pin_d5=Y7_GPIO_NUM;
    cfg.pin_d6=Y8_GPIO_NUM; cfg.pin_d7=Y9_GPIO_NUM;
    cfg.pin_xclk=XCLK_GPIO_NUM; cfg.pin_pclk=PCLK_GPIO_NUM;
    cfg.pin_vsync=VSYNC_GPIO_NUM; cfg.pin_href=HREF_GPIO_NUM;
    cfg.pin_sccb_sda=SIOD_GPIO_NUM; cfg.pin_sccb_scl=SIOC_GPIO_NUM;
    cfg.pin_pwdn=PWDN_GPIO_NUM; cfg.pin_reset=RESET_GPIO_NUM;
    cfg.xclk_freq_hz=20000000; cfg.pixel_format=PIXFORMAT_GRAYSCALE;
    cfg.frame_size=FRAMESIZE_QVGA; cfg.fb_count=1;
    cfg.grab_mode=CAMERA_GRAB_LATEST;
    esp_err_t err=esp_camera_init(&cfg);
    if(err!=ESP_OK){Serial.printf("[CAM] Failed: 0x%x\n",err);return false;}
    Serial.println("[CAM] OK"); return true;
}

// ─────────────────────────────────────────────
// CV — OPTICAL FLOW CLIMBER TRACKER
// ─────────────────────────────────────────────

void cv_process(camera_fb_t* fb) {
    if(!fb) return;
    uint8_t* px=fb->buf; int w=fb->width,h=fb->height;
    long sy=0,cnt=0; uint8_t thr=80;

    for(int y=0;y<h;y++) for(int x=0;x<w;x++)
        if(px[y*w+x]<thr){sy+=y;cnt++;}

    if(cnt>500){
        g_cv_detected=true;
        int cy=(int)(sy/cnt);
        const float WALL_H=15.0f; // tune to wall height in meters
        g_cv_height=WALL_H*(1.0f-(float)cy/(float)h);
        if(g_prev_cy>0){
            int dy=g_prev_cy-cy;
            if(dy==0 && g_cv_height>1.5f)
                g_cv_clip_conf=min((float)g_cv_clip_conf+0.15f,1.0f);
            else
                g_cv_clip_conf=max((float)g_cv_clip_conf-0.10f,0.0f);
        }
        g_prev_cy=cy;
    } else {
        g_cv_detected=false;
        g_cv_clip_conf=max((float)g_cv_clip_conf-0.20f,0.0f);
        g_prev_cy=-1;
    }
}

// ─────────────────────────────────────────────
// BLE PROVISIONING — CALLBACKS
// ─────────────────────────────────────────────

class WiFiCharCallback : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* c) override {
        StaticJsonDocument<256> doc;
        if(deserializeJson(doc,c->getValue())==DeserializationError::Ok){
            g_prov.ssid=doc["ssid"].as<String>();
            g_prov.password=doc["password"].as<String>();
            g_prov.wifiReceived=true;
            Serial.println("[BLE] WiFi creds received");
        }
    }
};

class GymCharCallback : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* c) override {
        StaticJsonDocument<256> doc;
        if(deserializeJson(doc,c->getValue())==DeserializationError::Ok){
            g_prov.gymId=doc["gymId"].as<String>();
            g_prov.deviceId=doc["deviceId"].as<String>();
            g_prov.gymReceived=true;
            Serial.println("[BLE] Gym config received");
            if(g_prov.wifiReceived){
                prefs.begin("aria",false);
                prefs.putString("wifi_ssid",g_prov.ssid);
                prefs.putString("wifi_pass",g_prov.password);
                prefs.putString("gym_id",g_prov.gymId);
                prefs.putString("device_id",g_prov.deviceId);
                prefs.putBool("provisioned",true);
                prefs.putUInt("total_falls",0);
                prefs.putUInt("cycle_count",0);
                prefs.end();
                Serial.printf("[BLE] Saved gym=%s device=%s — rebooting\n",
                    g_prov.gymId.c_str(),g_prov.deviceId.c_str());
                if(g_status_char){g_status_char->setValue("OK");g_status_char->notify();}
                delay(500); ESP.restart();
            } else {
                if(g_status_char){g_status_char->setValue("ERR:NO_WIFI");g_status_char->notify();}
            }
        }
    }
};

// ─────────────────────────────────────────────
// BLE PROVISIONING — CONTROL
// ─────────────────────────────────────────────

bool isProvisioned(){
    prefs.begin("aria",true); bool r=prefs.getBool("provisioned",false); prefs.end(); return r;
}

void clearProvisioning(){
    prefs.begin("aria",false); prefs.clear(); prefs.end();
    Serial.println("[NVS] Cleared — rebooting"); delay(500); ESP.restart();
}

void loadConfig(){
    prefs.begin("aria",true);
    String ssid=prefs.getString("wifi_ssid","");
    String pass=prefs.getString("wifi_pass","");
    g_gym_id=prefs.getString("gym_id","");
    g_device_id=prefs.getString("device_id","");
    g_total_falls=prefs.getUInt("total_falls",0);
    g_cycle_count=prefs.getUInt("cycle_count",0);
    prefs.end();
    Serial.printf("[CFG] gym=%s device=%s falls=%u cycles=%u\n",
        g_gym_id.c_str(),g_device_id.c_str(),g_total_falls,g_cycle_count);

    WiFi.begin(ssid.c_str(),pass.c_str());
    Serial.print("[WiFi] Connecting");
    for(int i=0;i<40&&WiFi.status()!=WL_CONNECTED;i++){delay(500);Serial.print(".");}
    if(WiFi.status()==WL_CONNECTED){
        Serial.printf("\n[WiFi] Connected: %s\n",WiFi.localIP().toString().c_str());
        g_wifi_connected=true;
    } else {
        Serial.println("\n[WiFi] FAILED — offline mode");
    }
}

void runProvisioningMode(){
    Serial.println("[BLE] Provisioning mode");
    uint8_t mac[6]; esp_read_mac(mac,ESP_MAC_BT);
    char name[16]; snprintf(name,sizeof(name),"ARIA-%02X%02X%02X",mac[3],mac[4],mac[5]);

    BLEDevice::init(name);
    BLEServer* srv=BLEDevice::createServer();
    BLEService* svc=srv->createService(PROVISIONING_SERVICE_UUID);

    BLECharacteristic* wc=svc->createCharacteristic(WIFI_CHAR_UUID,BLECharacteristic::PROPERTY_WRITE);
    wc->setCallbacks(new WiFiCharCallback());

    BLECharacteristic* gc=svc->createCharacteristic(GYM_CHAR_UUID,BLECharacteristic::PROPERTY_WRITE);
    gc->setCallbacks(new GymCharCallback());

    g_status_char=svc->createCharacteristic(STATUS_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ|BLECharacteristic::PROPERTY_NOTIFY);
    g_status_char->addDescriptor(new BLE2902());
    g_status_char->setValue("WAITING");

    svc->start(); BLEDevice::startAdvertising();
    Serial.printf("[BLE] Advertising as '%s' — waiting for ARIA app\n",name);
    while(true) delay(100);
}

// ─────────────────────────────────────────────
// FIREBASE — AUTH
// ─────────────────────────────────────────────

bool firebase_get_token(){
    if(!g_wifi_connected) return false;
    HTTPClient http;
    String url="https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=";
    url+=FIREBASE_API_KEY;
    http.begin(url); http.addHeader("Content-Type","application/json");
    int code=http.POST("{\"returnSecureToken\":true}");
    if(code==200){
        StaticJsonDocument<512> doc; deserializeJson(doc,http.getString());
        g_firebase_token=doc["idToken"].as<String>();
        http.end(); Serial.println("[Firebase] Auth OK"); return true;
    }
    Serial.printf("[Firebase] Auth failed HTTP %d\n",code); http.end(); return false;
}

// ─────────────────────────────────────────────
// FIREBASE — HEARTBEAT
// ─────────────────────────────────────────────

void firebase_push_heartbeat(){
    if(!g_wifi_connected||g_gym_id.isEmpty()||g_firebase_token.isEmpty()) return;
    uint32_t uptime=(millis()-g_uptime_start)/1000;

    StaticJsonDocument<768> doc;
    JsonObject f=doc.createNestedObject("fields");
    f["state"]["stringValue"]=state_to_string(g_stm_state);
    f["tension"]["doubleValue"]=(double)g_stm_tension;
    f["motorPosition"]["doubleValue"]=(double)g_stm_rope_pos;
    f["ropeOut"]["doubleValue"]=(double)g_cv_height;
    f["isOnline"]["booleanValue"]=true;
    f["uptimeSeconds"]["integerValue"]=(int)uptime;
    f["totalFallsCaught"]["integerValue"]=(int)g_total_falls;
    f["cycleCount"]["integerValue"]=(int)g_cycle_count;
    f["lastHeartbeat"]["serverValue"]="REQUEST_TIME";  // Firestore fills in server timestamp

    String body; serializeJson(doc,body);
    String url=String(FIREBASE_BASE_URL)+"/gyms/"+g_gym_id+"/devices/"+g_device_id
              +"?updateMask.fieldPaths=state&updateMask.fieldPaths=tension"
              +"&updateMask.fieldPaths=motorPosition&updateMask.fieldPaths=ropeOut"
              +"&updateMask.fieldPaths=isOnline&updateMask.fieldPaths=uptimeSeconds"
              +"&updateMask.fieldPaths=totalFallsCaught&updateMask.fieldPaths=cycleCount"
              +"&updateMask.fieldPaths=lastHeartbeat";

    HTTPClient http; http.begin(url);
    http.addHeader("Content-Type","application/json");
    http.addHeader("Authorization","Bearer "+g_firebase_token);
    int code=http.sendRequest("PATCH",body);
    if(code==401){http.end();if(firebase_get_token())firebase_push_heartbeat();return;}
    if(code!=200) Serial.printf("[Firebase] Heartbeat failed: %d\n",code);
    http.end();
}

// ─────────────────────────────────────────────
// FIREBASE — EVENT PUSH
// ─────────────────────────────────────────────

void firebase_push_event(const char* type, JsonObject& pf){
    if(!g_wifi_connected||g_firebase_token.isEmpty()) return;
    StaticJsonDocument<768> doc;
    JsonObject f=doc.createNestedObject("fields");
    f["type"]["stringValue"]=type;
    f["deviceId"]["stringValue"]=g_device_id.c_str();
    f["gymId"]["stringValue"]=g_gym_id.c_str();
    f["sessionId"]["nullValue"]=nullptr;
    f["timestamp"]["stringValue"]=String(millis()/1000);
    JsonObject pm=f["payload"].createNestedObject("mapValue").createNestedObject("fields");
    for(JsonPair kv:pf) pm[kv.key()]=kv.value();
    String body; serializeJson(doc,body);
    String url=String(FIREBASE_BASE_URL)+"/gyms/"+g_gym_id+"/devices/"+g_device_id+"/events";
    HTTPClient http; http.begin(url);
    http.addHeader("Content-Type","application/json");
    http.addHeader("Authorization","Bearer "+g_firebase_token);
    int code=http.POST(body);
    Serial.printf("[Firebase] Event '%s': %d\n",type,code);
    http.end();
}

void firebase_push_fall_event(float peakTension, float fallHeight){
    g_total_falls++; g_cycle_count++;
    prefs.begin("aria",false);
    prefs.putUInt("total_falls",g_total_falls);
    prefs.putUInt("cycle_count",g_cycle_count);
    prefs.end();
    StaticJsonDocument<128> pd; JsonObject p=pd.to<JsonObject>();
    p["peakTension"]["doubleValue"]=(double)peakTension;
    p["fallHeight"]["doubleValue"]=(double)fallHeight;
    p["type"]["stringValue"]="FALL_CAUGHT";
    firebase_push_event("FALL_CAUGHT",p);
}

void firebase_push_voice_event(VoiceCmd cmd, float conf){
    const char* s="unknown";
    for(int i=0;i<LABEL_MAP_LEN;i++) if(LABEL_MAP[i].cmd==cmd){s=LABEL_MAP[i].label;break;}
    StaticJsonDocument<128> pd; JsonObject p=pd.to<JsonObject>();
    p["command"]["stringValue"]=s;
    p["confidence"]["doubleValue"]=(double)conf;
    p["type"]["stringValue"]="VOICE_CMD";
    firebase_push_event("VOICE_CMD",p);
}

void firebase_push_state_change(int from, int to, const char* by){
    StaticJsonDocument<128> pd; JsonObject p=pd.to<JsonObject>();
    p["fromState"]["stringValue"]=state_to_string(from);
    p["toState"]["stringValue"]=state_to_string(to);
    p["triggeredBy"]["stringValue"]=by;
    p["type"]["stringValue"]="STATE_CHANGE";
    firebase_push_event("STATE_CHANGE",p);
}

// ─────────────────────────────────────────────
// FIREBASE — COMMAND POLLING
// ─────────────────────────────────────────────

void firebase_poll_commands(){
    if(!g_wifi_connected||g_firebase_token.isEmpty()) return;
    HTTPClient http;
    http.begin(String(FIREBASE_BASE_URL)+"/commands/"+g_device_id);
    http.addHeader("Authorization","Bearer "+g_firebase_token);
    int code=http.GET();
    if(code!=200){if(code!=404)Serial.printf("[Firebase] Poll: %d\n",code);http.end();return;}
    StaticJsonDocument<512> doc; deserializeJson(doc,http.getString()); http.end();
    const char* result=doc["fields"]["result"]["stringValue"];
    if(!result||strcmp(result,"PENDING")!=0) return;
    const char* cmd=doc["fields"]["command"]["stringValue"];
    if(!cmd) return;
    Serial.printf("[Firebase] Command: %s\n",cmd);
    if     (strcmp(cmd,"PAUSE_MOTOR")==0)       STM32Serial.println("CMD:PAUSE");
    else if(strcmp(cmd,"RESUME_MOTOR")==0)      STM32Serial.println("CMD:RESUME");
    else if(strcmp(cmd,"LOCKOUT")==0)           STM32Serial.println("CMD:LOCKOUT");
    else if(strcmp(cmd,"RETURN_TO_SERVICE")==0) STM32Serial.println("CMD:RETURN");
    else if(strcmp(cmd,"CALIBRATE_ENCODER")==0) STM32Serial.println("CMD:CALIBRATE");
    else if(strcmp(cmd,"REBOOT")==0){delay(200);ESP.restart();}

    // Acknowledge
    String aurl=String(FIREBASE_BASE_URL)+"/commands/"+g_device_id
               +"?updateMask.fieldPaths=result&updateMask.fieldPaths=acknowledged";
    StaticJsonDocument<128> ack;
    ack["fields"]["result"]["stringValue"]="SUCCESS";
    ack["fields"]["acknowledged"]["booleanValue"]=true;
    String ab; serializeJson(ack,ab);
    HTTPClient ah; ah.begin(aurl);
    ah.addHeader("Content-Type","application/json");
    ah.addHeader("Authorization","Bearer "+g_firebase_token);
    ah.sendRequest("PATCH",ab); ah.end();
}

// ─────────────────────────────────────────────
// FREERTOS TASK 1 — VOICE (Core 0)
// ─────────────────────────────────────────────

void voice_task(void* p) {
    Serial.println("[TASK] Voice started");

    // ── PLACEHOLDER — replace with Edge Impulse inference loop ───────────────
    // After training your model at studio.edgeimpulse.com:
    //
    // while(true){
    //   if(microphone_inference_record()){
    //     signal_t sig;
    //     microphone_inference_signal_get_data(0,0,&sig);
    //     ei_impulse_result_t result;
    //     run_classifier_continuous(&sig,&result,false);
    //     float best=0; int bidx=-1;
    //     for(int i=0;i<EI_CLASSIFIER_LABEL_COUNT;i++){
    //       if(result.classification[i].value>best){
    //         best=result.classification[i].value; bidx=i;}}
    //     if(best>=VOICE_CONF_MIN && bidx>=0){
    //       const char* lbl=ei_classifier_inferencing_categories[bidx];
    //       for(int j=0;j<LABEL_MAP_LEN;j++){
    //         if(strcmp(lbl,LABEL_MAP[j].label)==0){
    //           uart_send_voice(LABEL_MAP[j].cmd,best);
    //           firebase_push_voice_event(LABEL_MAP[j].cmd,best);}}}
    //   }
    //   vTaskDelay(pdMS_TO_TICKS(10));}
    // ─────────────────────────────────────────────────────────────────────────

    while(true) vTaskDelay(pdMS_TO_TICKS(50));
}

// ─────────────────────────────────────────────
// FREERTOS TASK 2 — CV (Core 0)
// ─────────────────────────────────────────────

void cv_task(void* p) {
    Serial.println("[TASK] CV started");
    if(!camera_init()){vTaskDelete(NULL);return;}
    while(true){
        camera_fb_t* fb=esp_camera_fb_get();
        if(fb){cv_process(fb);esp_camera_fb_return(fb);
               uart_send_cv(g_cv_clip_conf,g_cv_height,g_cv_detected);}
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

// ─────────────────────────────────────────────
// FREERTOS TASK 3 — UART (Core 1)
// ─────────────────────────────────────────────

void uart_task(void* p) {
    Serial.println("[TASK] UART started");
    while(true){
        while(STM32Serial.available()){
            uint8_t c=(uint8_t)STM32Serial.read();
            if(c==PKT0){uart_handle_binary(c);continue;}
            if((char)c=='\n'){g_ubuf[g_uidx]='\0';uart_parse(g_ubuf);g_uidx=0;}
            else if(g_uidx<UART_BUF_SIZE-1){g_ubuf[g_uidx++]=(char)c;uart_handle_binary(c);}
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

// ─────────────────────────────────────────────
// FREERTOS TASK 4 — FIREBASE (Core 1)
// ─────────────────────────────────────────────

void firebase_task(void* p) {
    Serial.println("[TASK] Firebase started");
    for(int i=0;!firebase_get_token()&&i<5;i++){
        Serial.printf("[Firebase] Auth retry %d/5\n",i+1);
        vTaskDelay(pdMS_TO_TICKS(3000));
    }
    uint32_t last_hb=0,last_poll=0;
    float    last_tension=0.0f;
    int      last_state=-1;
    while(true){
        uint32_t now=millis();
        if(now-last_hb>HEARTBEAT_INTERVAL_MS){firebase_push_heartbeat();last_hb=now;}
        if(now-last_poll>CMD_POLL_INTERVAL_MS){firebase_poll_commands();last_poll=now;}
        // Fall detection
        float delta=g_stm_tension-last_tension;
        if(g_stm_state==1 && delta>FALL_TENSION_DELTA){
            Serial.printf("[EVENT] Fall — peak=%.1fkg h=%.1fm\n",(float)g_stm_tension,(float)g_cv_height);
            firebase_push_fall_event(g_stm_tension,g_cv_height);
        }
        last_tension=g_stm_tension;
        // State change detection
        if(last_state>=0 && g_stm_state!=last_state)
            firebase_push_state_change(last_state,g_stm_state,"system");
        last_state=g_stm_state;
        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

// ─────────────────────────────────────────────
// SETUP
// ─────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("═══════════════════════════════════════════");
    Serial.println("  ARIA ESP32-S3 Intelligence Layer  v0.3.0 ");
    Serial.println("═══════════════════════════════════════════");

    STM32Serial.begin(UART_BAUD,SERIAL_8N1,STM32_UART_RX,STM32_UART_TX);
    Serial.println("[UART] STM32 serial ready");

    if(!isProvisioned()) runProvisioningMode();  // never returns

    loadConfig();
    g_uptime_start=millis();

    xTaskCreatePinnedToCore(voice_task,    "voice", 8192, NULL, 2, &h_voice,    0);
    xTaskCreatePinnedToCore(cv_task,       "cv",    8192, NULL, 1, &h_cv,       0);
    xTaskCreatePinnedToCore(uart_task,     "uart",  4096, NULL, 3, &h_uart,     1);
    xTaskCreatePinnedToCore(firebase_task, "fb",    8192, NULL, 2, &h_firebase, 1);

    Serial.printf("[ARIA] Ready — device=%s gym=%s\n",
                  g_device_id.c_str(),g_gym_id.c_str());
}

// ─────────────────────────────────────────────
// LOOP — status + serial debug commands
// ─────────────────────────────────────────────

void loop() {
    static uint32_t last_print=0;
    if(millis()-last_print>5000){
        last_print=millis();
        Serial.printf("[STATUS] state=%-10s tension=%5.1fkg rope=%5.2fm | "
                      "CV h=%4.1fm clip=%.2f det=%d | WiFi=%s falls=%u\n",
                      state_to_string(g_stm_state),(float)g_stm_tension,(float)g_stm_rope_pos,
                      (float)g_cv_height,(float)g_cv_clip_conf,(int)g_cv_detected,
                      g_wifi_connected?"OK":"NO",g_total_falls);
    }

    // Serial monitor commands:
    //   reset   — factory reset NVS, reboot into BLE provisioning
    //   token   — force refresh Firebase auth token
    //   status  — full status dump
    if(Serial.available()){
        String cmd=Serial.readStringUntil('\n'); cmd.trim();
        if(cmd=="reset"){
            clearProvisioning();
        } else if(cmd=="token"){
            firebase_get_token()
                ? Serial.println("[CMD] Token OK")
                : Serial.println("[CMD] Token FAILED");
        } else if(cmd=="status"){
            Serial.println("──── ARIA Status ────");
            Serial.printf("  Device  : %s\n",g_device_id.c_str());
            Serial.printf("  Gym     : %s\n",g_gym_id.c_str());
            Serial.printf("  WiFi    : %s  %s\n",
                g_wifi_connected?"Connected":"Offline",
                WiFi.localIP().toString().c_str());
            Serial.printf("  Firebase: %s\n",
                g_firebase_token.isEmpty()?"No token":"Authenticated");
            Serial.printf("  State   : %s\n",state_to_string(g_stm_state));
            Serial.printf("  Tension : %.1f kg\n",(float)g_stm_tension);
            Serial.printf("  Falls   : %u  Cycles: %u\n",g_total_falls,g_cycle_count);
            Serial.printf("  Uptime  : %lu s\n",(millis()-g_uptime_start)/1000);
            Serial.println("─────────────────────");
        }
    }
    delay(100);
}