/*
  esp32_camera_backup.ino — XIAO ESP32S3 Sense를 USB 시리얼로 라즈베리파이에
  직결해서 쓰는 백업 카메라. 라즈베리파이 CSI 카메라(리본 케이블) 인식 문제
  (2026.08.27)의 대안으로 작성. WiFi 버전은 발열 문제로 이 방식으로 변경.

  동작: 라즈베리파이가 시리얼로 "CAPTURE\n"을 보내면, 이 보드가 사진을
  찍어서 "다음 줄에 파일 크기(바이트 수), 그 다음 그만큼의 JPEG 바이트"
  순서로 돌려준다. 아두이노 우노 안전센서(JSON 시리얼)와 같은 원리 —
  USB 케이블 하나로 전원+통신 다 됨, WiFi 불필요.

  준비:
  1. 보드 설정: Tools → Board → XIAO_ESP32S3, PSRAM: OPI PSRAM 켜기
     (카메라 프레임버퍼 저장에 필요 — 꺼져있으면 초기화 실패함)
  2. 업로드 후 USB로 라즈베리파이에 연결
  3. Pi에서 시리얼 포트 확인(`ls /dev/ttyACM* /dev/ttyUSB*`) 후
     esp32_cam_client.py로 테스트
*/

#include "esp_camera.h"

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
    Serial.printf("CAMERA_INIT_FAILED 0x%x\n", err);
  } else {
    Serial.println("CAMERA_READY");
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  startCamera();
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "CAPTURE") {
      camera_fb_t* fb = esp_camera_fb_get();
      if (!fb) {
        Serial.println("0");  // 실패 시 크기 0 전송
        return;
      }
      Serial.println(fb->len);   // 먼저 바이트 수를 한 줄로 전송
      Serial.write(fb->buf, fb->len);  // 그 다음 JPEG 원본 바이트 전송
      esp_camera_fb_return(fb);
    }
  }
}
