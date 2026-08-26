/*
  arduino_safety_monitor.ino — LostPatrol 안전센서(FLAME + LM35DZ + 소음센서)
  + LCD1602(I2C, 텍스트 상태 표시) + OLED(I2C, RoboEyes 애니메이션 얼굴)

  FLAME/온도/소음 값을 1초에 한 줄씩 JSON으로 시리얼 출력한다.
  Raspberry Pi의 robot_이윤정/mock_controller/safety_monitor.py가 이 형식을
  그대로 읽는다 (docs/HARDWARE_REFERENCE.md의 제안 프로토콜과 동일):
      {"flame": 0, "temp_c": 26.4, "sound": 0}

  배선 (실제 연결 기준, 2026.08.26~27):
    FLAME 센서(2다리 포토트랜지스터형) 짧은다리→5V, 긴다리→A0 + 10kΩ 저항 거쳐 GND
    소음센서 모듈(비교기 내장, DO 있음)  +→5V, G→GND, DO→A2
    LM35DZ (평평한 면 기준 왼쪽부터)     왼쪽(VCC)→5V, 가운데(OUT)→A1, 오른쪽(GND)→GND
    LCD1602 I2C 모듈                    VCC→5V, GND→GND, SDA→A4, SCL→A5 (주소 0x27)
    OLED(SSD1306, I2C)                  VDD→5V, GND→GND, SCK→A5, SDA→A4 (주소 0x3C)
      → LCD랑 OLED는 같은 I2C 버스(A4/A5)에 주소만 다르게 병렬로 같이 연결.

  라이브러리: "LiquidCrystal I2C", "Adafruit GFX Library", "Adafruit SSD1306",
  "FluxGarage RoboEyes"를 Arduino IDE 라이브러리 관리자에서 설치.

  참고: A0~A5는 아날로그 전용이 아니라 digitalRead()/digitalWrite()도 그대로
  지원하는 핀이다.

  ## 디버깅 이력 (2026.08.26)
  1차: 소음/LM35DZ 핀이 코드와 반대로 배선돼있어서 temp_c가 항상
       499.5(ADC 최댓값)로, sound가 항상 0으로 고정됨 → 실제 배선(A1/A2)에
       맞춰 코드 수정으로 해결.
  2차: FLAME 센서가 비교기 내장 모듈이 아니라 포토트랜지스터+저항으로 직접
       구성한 아날로그 회로인데 digitalRead()로 읽어서 flame이 계속 1로
       고정됨. analogRead()로 바꿈.
  3차: 임계값을 500으로 뒀더니 이번엔 항상 0(전혀 안 오름) — 이 회로는
       실측 결과 값의 범위 자체가 아주 작아서(수십 단위도 안 됨) 500은
       터무니없이 높은 값이었음. 실물 테스트(라이터 반응 시 LED 켜지는
       것까지 확인)로 5로 낮춰서 정상 동작 확인함.
  4차: 소음센서(DO만 있는 모듈)는 트리머로 감도 조정해서 평소 0, 큰 소리에만
       1로 반응하도록 캘리브레이션 완료.
  5차: temp_c가 5.9~73.7도로 튀는 현상 발견 — 한 번의 analogRead() 값을
       그대로 쓰던 걸 여러 번 읽어 평균 내는 방식(readAverage())으로 바꿔서
       안정화.
  6~8차: LCD1602 위에 텍스트/커스텀 픽셀 문자로 눈 깜빡임+곁눈질 애니메이션을
       직접 구현했었으나(커밋 이력 참고), 결국 LCD는 텍스트 전용으로 쓰고
       진짜 애니메이션은 OLED+RoboEyes 라이브러리로 분리하기로 함(2026.08.27).
  9차: RoboEyes는 부드럽게 움직이려면 update()를 자주(매 루프) 호출해야
       하는데, 기존 loop()는 센서 평균값 계산(readAverage, 딜레이 포함)
       때문에 1초에 한 바퀴만 돎 → millis() 기반으로 "센서 읽기는 1초마다,
       RoboEyes.update()는 매 루프"로 구조를 분리해서 애니메이션이
       끊기지 않게 함.
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <FluxGarage_RoboEyes.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);  // 주소, 컬럼 수, 행 수

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64  // OLED가 128x32짜리면 32로 변경

roboEyes eyes;  // 내부적으로 SSD1306(기본 주소 0x3C)을 직접 초기화함

const int FLAME_PIN = A0;  // 아날로그로 읽음 (포토트랜지스터+저항 회로)
const int SOUND_PIN = A2;  // 디지털로 읽음 (DO, 트리머로 감도 캘리브레이션 완료)
const int TEMP_PIN = A1;   // 아날로그 (LM35DZ)

// 실물 테스트로 확정(2026.08.26) — 라이터 반응 시 LED 켜지는 것까지 확인.
const int FLAME_THRESHOLD = 5;

const int SAMPLE_COUNT = 10;   // 평균낼 샘플 개수
const int SAMPLE_DELAY_MS = 5; // 샘플 사이 간격

const unsigned long SENSOR_INTERVAL_MS = 1000;  // 센서 읽기/LCD/시리얼 갱신 주기
unsigned long lastSensorRead = 0;

enum Mood { MOOD_NORMAL, MOOD_FIRE, MOOD_LOUD };
Mood lastMood = MOOD_NORMAL;
Mood lastLcdMood = MOOD_NORMAL;  // LCD는 값이 바뀔 때만 다시 그려서 깜빡임 방지

void setup() {
  Serial.begin(9600);
  pinMode(SOUND_PIN, INPUT);

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("LostPatrol");
  lcd.setCursor(0, 1);
  lcd.print("Status: NORMAL");

  eyes.begin(SCREEN_WIDTH, SCREEN_HEIGHT, 60);  // 화면 크기, 목표 프레임레이트(fps)
  eyes.setAutoblinker(ON, 3, 2);  // 자동 눈깜빡임: 3초 간격(±2초 변동)
  eyes.setIdleMode(ON, 2, 2);     // 가만히 있을 때 자동으로 이곳저곳 둘러봄
  eyes.setMood(DEFAULT);
}

// 여러 번 읽어서 평균낸 값을 돌려준다 — analogRead() 한 번만 쓰면 순간
// 노이즈로 값이 크게 튀는 문제(temp_c가 5.9~73.7도로 튀던 것)가 있어서 추가함.
int readAverage(int pin) {
  long sum = 0;
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    sum += analogRead(pin);
    delay(SAMPLE_DELAY_MS);
  }
  return sum / SAMPLE_COUNT;
}

void updateLcd(Mood mood, float tempC, int flame, int sound) {
  if (mood == lastLcdMood) return;  // 상태 그대로면 다시 그리지 않음(깜빡임 방지)
  lastLcdMood = mood;

  lcd.setCursor(0, 0);
  lcd.print("T:");
  lcd.print(tempC, 1);
  lcd.print("C          ");  // 뒤에 남는 이전 글자 지우기용 공백

  lcd.setCursor(0, 1);
  switch (mood) {
    case MOOD_FIRE:
      lcd.print("Status: FIRE!!  ");
      break;
    case MOOD_LOUD:
      lcd.print("Status: LOUD    ");
      break;
    case MOOD_NORMAL:
    default:
      lcd.print("Status: NORMAL  ");
      break;
  }
}

void updateEyesMood(Mood mood) {
  if (mood == lastMood) return;  // 상태 그대로면 다시 호출 안 함
  lastMood = mood;

  switch (mood) {
    case MOOD_FIRE:
      eyes.setMood(ANGRY);
      eyes.anim_confused();  // 위험 신호로 한 번 흔들리는 모션
      break;
    case MOOD_LOUD:
      eyes.setMood(HAPPY);   // 눈이 커지는 느낌으로 놀란 표정 대체 표현
      eyes.anim_laugh();
      break;
    case MOOD_NORMAL:
    default:
      eyes.setMood(DEFAULT);
      break;
  }
}

void loop() {
  // RoboEyes는 매 루프 최대한 자주 update()를 호출해야 부드럽게 움직인다.
  eyes.update();

  unsigned long now = millis();
  if (now - lastSensorRead < SENSOR_INTERVAL_MS) return;  // 아직 1초 안 지남
  lastSensorRead = now;

  int flameRaw = readAverage(FLAME_PIN);
  int soundRaw = digitalRead(SOUND_PIN);
  int tempRaw = readAverage(TEMP_PIN);

  int flame = (flameRaw > FLAME_THRESHOLD) ? 1 : 0;
  int sound = (soundRaw == HIGH) ? 1 : 0;

  // LM35DZ: 10mV/°C, Arduino 5V 기준전압 기준 변환 공식
  float tempC = (tempRaw * 5.0 / 1024.0) * 100.0;

  Serial.print("{\"flame\": ");
  Serial.print(flame);
  Serial.print(", \"temp_c\": ");
  Serial.print(tempC, 1);
  Serial.print(", \"sound\": ");
  Serial.print(sound);
  Serial.println("}");

  // 우선순위: 불꽃 > 큰 소리 > 평온. (둘 다 감지되면 더 위험한 불꽃 표정 우선)
  Mood mood = MOOD_NORMAL;
  if (flame) {
    mood = MOOD_FIRE;
  } else if (sound) {
    mood = MOOD_LOUD;
  }

  updateEyesMood(mood);
  updateLcd(mood, tempC, flame, sound);
}
