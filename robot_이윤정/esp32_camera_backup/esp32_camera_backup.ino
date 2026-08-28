/*
  esp32_camera_backup.ino — XIAO ESP32S3 Sense를 임시 카메라로 쓰기 위한
  최소 웹서버. 라즈베리파이 CSI 카메라(리본 케이블)가 갑자기 인식이 안 되는
  문제(2026.08.27, 시연 촬영 도중 발생)의 백업 대안으로 작성.

  WiFi로 접속해서 http://<이 보드의 IP>/capture 로 요청하면 사진 한 장(JPEG)을
  돌려준다. controller.py가 rpicam-still 대신 이 주소에서 사진을 받아오도록
  바꾸면, 라즈베리파이 카메라 없이도 분실물 감지 파이프라인을 그대로 쓸 수 있다.

  준비:
  1. 아래 WIFI_SSID / WIFI_PASSWORD를 본인 WiFi로 채우기
  2. 보드 설정: Tools → Board → XIAO_ESP32S3, PSRAM: OPI PSRAM 로 켜기
     (카메라 프레임버퍼 저장에 PSRAM이 필요함 — 꺼져있으면 초기화 실패함)
  3. 업로드 후 시리얼 모니터(115200 baud)에서 나오는 IP 주소 확인
  4. 브라우저로 http://<IP>/capture 접속해서 사진 뜨는지 확인
*/

#include "esp_camera.h"
#include <WiFi.h>

// XIAO ESP32S3 Sense 카메라 핀 정의 (보드 자체 카메라 커넥터용, 고정값)
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     10
#define SIOD_GPIO_NUM     40
#define SIOC_GPIO_NUM     39
#define Y9_GPIO_NUM       48
#define Y8_GPIO_NUM       11
#define Y7_GPIO_NUM       12
#define Y6_GPIO_NUM       14
#define Y5_GPIO_NUM       16
#define Y4_GPIO_NUM       18
#define Y3_GPIO_NUM       17
#define Y2_GPIO_NUM       15
#define VSYNC_GPIO_NUM    38
#define HREF_GPIO_NUM     47
#define PCLK_GPIO_NUM     13

const char* WIFI_SSID = "여기에_와이파이_이름";
const char* WIFI_PASSWORD = "여기에_비밀번호";

WiFiServer server(80);

void startCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;  // 640x480
  config.jpeg_quality = 12;           // 낮을수록 고화질(파일은 커짐), 0~63
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("카메라 초기화 실패: 0x%x (PSRAM이 꺼져있으면 이 에러가 남)\n", err);
  } else {
    Serial.println("카메라 초기화 성공");
  }
}

void handleCapture(WiFiClient& client) {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    client.println("HTTP/1.1 500 Internal Server Error");
    client.println();
    return;
  }
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: image/jpeg");
  client.print("Content-Length: ");
  client.println(fb->len);
  client.println("Connection: close");
  client.println();
  client.write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  startCamera();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("WiFi 연결 중");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP 주소: ");
  Serial.println(WiFi.localIP());
  Serial.println("사진 확인: http://<위 IP 주소>/capture");

  server.begin();
}

void loop() {
  WiFiClient client = server.available();
  if (!client) return;

  String request = client.readStringUntil('\r');
  client.flush();

  if (request.indexOf("GET /capture") >= 0) {
    handleCapture(client);
  } else {
    client.println("HTTP/1.1 404 Not Found");
    client.println();
  }
  client.stop();
}
