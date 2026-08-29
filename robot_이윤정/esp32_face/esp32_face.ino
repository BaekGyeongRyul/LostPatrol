/*
  esp32_face.ino — LostPatrol 로봇 얼굴 (ESP32-C3 + OLED + RoboEyes)

  아두이노 우노(arduino_safety_monitor.ino)가 FLAME/소음 판정 결과를 디지털
  신호 2개로 그대로 넘겨주면, 이 ESP32가 그 신호만 읽어서 OLED에 RoboEyes로
  얼굴 표정을 그린다. WiFi도, 라즈베리파이 경유도 필요 없는 가장 단순한
  구조 — 우노와 ESP32는 신호선 2개 + 공통 GND로만 연결된다.

  아두이노 우노가 메모리(RAM 2KB)가 부족해서 LCD+OLED+RoboEyes를 한 보드에
  다 못 올렸던 문제(arduino_safety_monitor.ino 디버깅 이력 11차 참고)를
  ESP32(RAM 훨씬 넉넉함)로 얼굴 부분만 분리해서 해결함(2026.08.27).

  배선:
    우노 D8(flame신호) → ESP32 FLAME_IN_PIN
    우노 D9(sound신호) → ESP32 SOUND_IN_PIN
    우노 GND           → ESP32 GND (반드시 공통으로 연결해야 신호가 제대로 전달됨)
    OLED(SSD1306, I2C) VDD→3.3V, GND→GND, SCK→SCL_PIN, SDA→SDA_PIN (주소 0x3C)

  아래 핀 번호(FLAME_IN_PIN/SOUND_IN_PIN/SDA_PIN/SCL_PIN)는 보드마다 실제
  사용 가능한 GPIO가 달라서, 갖고 계신 ESP32-C3 보드 실크스크린(핀에 적힌
  번호)을 보고 맞는 번호로 바꿔야 할 수 있다. GPIO2/8/9은 부팅 스트래핑
  핀이라 가능하면 피해서 4/5/6/7번으로 잡아뒀다.

  라이브러리: "Adafruit GFX Library", "Adafruit SSD1306", "FluxGarage RoboEyes"
  (전부 Arduino IDE 라이브러리 관리자에서 설치 — 우노 쪽 작업할 때 이미
  설치했다면 그대로 재사용 가능, 보드 종류와 무관하게 공용임)
*/

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <FluxGarage_RoboEyes.h>

// 보드에 맞게 조정 필요 (실크스크린의 GPIO 번호 확인)
const int FLAME_IN_PIN = 4;
const int SOUND_IN_PIN = 5;
const int SDA_PIN = 6;
const int SCL_PIN = 7;

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64  // OLED가 128x32짜리면 32로 변경
#define OLED_ADDR 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
RoboEyes<Adafruit_SSD1306> eyes(display);

enum Mood { MOOD_NORMAL, MOOD_FIRE, MOOD_LOUD };
Mood lastMood = MOOD_NORMAL;

// 평소(NORMAL)에 가끔 웃는 표정을 잠깐 보여주기 위한 타이머.
bool isHappyNow = false;
unsigned long happyStartMs = 0;
unsigned long nextHappyMs = 0;
const unsigned long HAPPY_DURATION_MS = 2000;   // 웃는 표정 유지 시간
const unsigned long HAPPY_MIN_GAP_MS = 8000;    // 다음 웃음까지 최소 대기
const unsigned long HAPPY_MAX_GAP_MS = 15000;   // 다음 웃음까지 최대 대기

void setup() {
  Serial.begin(9600);
  pinMode(FLAME_IN_PIN, INPUT);
  pinMode(SOUND_IN_PIN, INPUT);

  Wire.begin(SDA_PIN, SCL_PIN);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("OLED 초기화 실패 — 주소/배선 확인 필요");
  }

  eyes.begin(SCREEN_WIDTH, SCREEN_HEIGHT, 60);  // 화면 크기, 목표 프레임레이트(fps)
  eyes.setAutoblinker(ON, 3, 2);  // 자동 눈깜빡임: 3초 간격(±2초 변동)
  eyes.setIdleMode(ON, 2, 2);     // 가만히 있을 때 자동으로 이곳저곳 둘러봄
  eyes.setMood(DEFAULT);
  nextHappyMs = millis() + random(HAPPY_MIN_GAP_MS, HAPPY_MAX_GAP_MS);
}

// 평소 상태일 때만, 일정 간격마다 잠깐 웃는 표정을 보여준다.
void updateIdleHappy(Mood mood) {
  if (mood != MOOD_NORMAL) return;  // 화재/큰소리 중엔 웃는 표정 끼어들지 않게
  unsigned long now = millis();

  if (isHappyNow) {
    if (now - happyStartMs >= HAPPY_DURATION_MS) {
      eyes.setMood(DEFAULT);
      isHappyNow = false;
      nextHappyMs = now + random(HAPPY_MIN_GAP_MS, HAPPY_MAX_GAP_MS);
    }
  } else if (now >= nextHappyMs) {
    eyes.setMood(HAPPY);
    isHappyNow = true;
    happyStartMs = now;
  }
}

void updateMood(Mood mood) {
  if (mood == lastMood) return;  // 상태 그대로면 다시 호출 안 함
  lastMood = mood;

  switch (mood) {
    case MOOD_FIRE:
    case MOOD_LOUD:
      // RoboEyes엔 "놀람" 표정이 따로 없어서, 화재/큰소리 둘 다 눈이
      // 흔들리는 애니메이션(anim_confused)으로 통일해서 놀란 느낌을 냄.
      eyes.setMood(DEFAULT);
      eyes.anim_confused();
      break;
    case MOOD_NORMAL:
    default:
      eyes.setMood(DEFAULT);
      isHappyNow = false;
      nextHappyMs = millis() + random(HAPPY_MIN_GAP_MS, HAPPY_MAX_GAP_MS);
      break;
  }
}

void loop() {
  // RoboEyes는 매 루프 최대한 자주 update()를 호출해야 부드럽게 움직인다.
  eyes.update();

  int flame = digitalRead(FLAME_IN_PIN);
  int sound = digitalRead(SOUND_IN_PIN);

  static unsigned long lastDebugMs = 0;  // 임시 디버그 — 원인 확인되면 지울 것
  if (millis() - lastDebugMs >= 500) {
    lastDebugMs = millis();
    Serial.print("flame=");
    Serial.print(flame);
    Serial.print(" sound=");
    Serial.println(sound);
  }

  // 우선순위: 불꽃 > 큰 소리 > 평온
  Mood mood = MOOD_NORMAL;
  if (flame == HIGH) {
    mood = MOOD_FIRE;
  } else if (sound == HIGH) {
    mood = MOOD_LOUD;
  }
  updateMood(mood);
  updateIdleHappy(mood);
}
