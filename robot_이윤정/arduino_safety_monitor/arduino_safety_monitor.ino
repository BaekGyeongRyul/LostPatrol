/*
  arduino_safety_monitor.ino — LostPatrol 안전센서(FLAME + LM35DZ + 소음센서)
  + LCD1602(I2C, 텍스트 상태 표시) + ESP32로 보내는 flame/sound 신호 핀

  FLAME/온도/소음 값을 1초에 한 줄씩 JSON으로 시리얼 출력한다.
  Raspberry Pi의 robot_이윤정/mock_controller/safety_monitor.py가 이 형식을
  그대로 읽는다 (docs/HARDWARE_REFERENCE.md의 제안 프로토콜과 동일):
      {"flame": 0, "temp_c": 26.4, "sound": 0}

  배선 (실제 연결 기준, 2026.08.26~27):
    FLAME 센서(2다리 포토트랜지스터형) 짧은다리→5V, 긴다리→A0 + 10kΩ 저항 거쳐 GND
    소음센서 모듈(비교기 내장, DO 있음)  +→5V, G→GND, DO→A2
    LM35DZ (평평한 면 기준 왼쪽부터)     왼쪽(VCC)→5V, 가운데(OUT)→A1, 오른쪽(GND)→GND
    LCD1602 I2C 모듈                    VCC→5V, GND→GND, SDA→A4, SCL→A5 (주소 0x27)
    ESP32(별도 보드, 얼굴용 OLED 담당)  D8→ESP32 GPIO(flame신호), D9→ESP32 GPIO(sound신호),
                                        GND→ESP32 GND(공통 기준전압 필수)

  라이브러리: "LiquidCrystal I2C"를 Arduino IDE 라이브러리 관리자에서 설치.

  참고: A0~A5는 아날로그 전용이 아니라 digitalRead()/digitalWrite()도 그대로
  지원하는 핀이다.

  ## 디버깅 이력 (2026.08.26~27)
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
  5차: temp_c가 5.9~73.7도로 튀는 현상 발견 → 한 번의 analogRead() 값을
       그대로 쓰던 걸 여러 번 읽어 평균 내는 방식(readAverage())으로 바꿔서
       안정화.
  6~9차: LCD1602+OLED(SSD1306)+RoboEyes를 전부 우노 한 대에 같이 올리려고
       시도했으나(커밋 이력 참고), display.begin()이 계속 실패함.
  10차: 남은 메모리를 출력해서 확인해보니 1058바이트 — OLED 프레임버퍼만
       1024바이트라 malloc이 실패하는 게 확정됨(우노 RAM은 총 2KB뿐).
       결론: 우노+LCD+OLED+RoboEyes 조합은 메모리가 근본적으로 부족.
  11차: 여분으로 있던 ESP32(RAM 훨씬 넉넉함)로 OLED+RoboEyes를 통째로
       분리하기로 함(2026.08.27). 우노는 원래 하던 센서+LCD만 담당하고,
       flame/sound 판정 결과만 디지털 신호 2개(D8/D9)로 ESP32에 넘겨준다
       (WiFi나 라즈베리파이 경유 없이 우노↔ESP32 직결 — 가장 단순한 방식).
  12차: temp_c가 계속 널뛰다가(9도~134도 등) 원인을 찾아보니 LM35DZ
       다리가 물리적으로 부러져 있었음(2026.08.27) — 그래서 접촉이
       불안정해서 뜬 값이 랜덤하게 잡혔던 것. 센서 교체 전까지는 TEMP_PIN
       읽기를 빼고 고정값(FIXED_TEMP_C)을 보내도록 임시 조치.
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);  // 주소, 컬럼 수, 행 수

const int FLAME_PIN = A0;  // 아날로그로 읽음 (포토트랜지스터+저항 회로)
const int SOUND_PIN = A2;  // 디지털로 읽음 (DO, 트리머로 감도 캘리브레이션 완료)

// LM35DZ 다리가 부러져서(2026.08.27) 실물 온도 측정을 일단 뺌 — 대신
// 고정된 정상값을 보내서 fire 판정(flame or temp>=DANGER)이 온도쪽
// 이상값 때문에 오작동하지 않게 함. 센서 교체/수리되면 TEMP_PIN 살리고
// readAverage(TEMP_PIN) 다시 쓰면 됨.
const float FIXED_TEMP_C = 25.0;

// ESP32로 flame/sound 판정 결과를 그대로 내보내는 디지털 출력 핀.
// ESP32는 이 두 핀만 읽어서 얼굴 표정을 결정한다 — 별도 프로토콜 없이
// 그냥 HIGH/LOW 신호만 주고받는 가장 단순한 방식.
const int FLAME_OUT_PIN = 8;
const int SOUND_OUT_PIN = 9;

// 화재 감지 시 켜지는 빨간 LED. 긴다리(+)→D7, 짧은다리(-)→GND
// (사이에 220~330Ω 저항 있으면 같이 연결)
const int FIRE_LED_PIN = 7;

// 실물 테스트로 확정(2026.08.26) — 라이터 반응 시 LED 켜지는 것까지 확인.
const int FLAME_THRESHOLD = 5;

const int SAMPLE_COUNT = 10;   // 평균낼 샘플 개수
const int SAMPLE_DELAY_MS = 5; // 샘플 사이 간격

enum Mood { MOOD_NORMAL, MOOD_FIRE, MOOD_LOUD };
Mood lastLcdMood = MOOD_NORMAL;  // LCD는 값이 바뀔 때만 다시 그려서 깜빡임 방지

void setup() {
  Serial.begin(9600);
  pinMode(SOUND_PIN, INPUT);
  pinMode(FLAME_OUT_PIN, OUTPUT);
  pinMode(SOUND_OUT_PIN, OUTPUT);
  pinMode(FIRE_LED_PIN, OUTPUT);
  digitalWrite(FLAME_OUT_PIN, LOW);
  digitalWrite(SOUND_OUT_PIN, LOW);

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("LostPatrol");
  lcd.setCursor(0, 1);
  lcd.print("Status: NORMAL");
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

void updateLcd(Mood mood, float tempC) {
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

void loop() {
  int flameRaw = readAverage(FLAME_PIN);
  int soundRaw = digitalRead(SOUND_PIN);

  int flame = (flameRaw > FLAME_THRESHOLD) ? 1 : 0;
  int sound = (soundRaw == HIGH) ? 1 : 0;

  // LM35DZ 다리 파손으로 실물 측정 대신 고정값 사용 (위 FIXED_TEMP_C 참고)
  float tempC = FIXED_TEMP_C;

  Serial.print("{\"flame\": ");
  Serial.print(flame);
  Serial.print(", \"temp_c\": ");
  Serial.print(tempC, 1);
  Serial.print(", \"sound\": ");
  Serial.print(sound);
  Serial.println("}");

  // ESP32로 그대로 신호 전달
  digitalWrite(FLAME_OUT_PIN, flame ? HIGH : LOW);
  digitalWrite(SOUND_OUT_PIN, sound ? HIGH : LOW);

  // 화재 감지 시 빨간 LED 켜기
  digitalWrite(FIRE_LED_PIN, flame ? HIGH : LOW);

  // 우선순위: 불꽃 > 큰 소리 > 평온. (둘 다 감지되면 더 위험한 불꽃 표정 우선)
  Mood mood = MOOD_NORMAL;
  if (flame) {
    mood = MOOD_FIRE;
  } else if (sound) {
    mood = MOOD_LOUD;
  }

  updateLcd(mood, tempC);

  delay(900);  // readAverage()가 이미 (10*5=50ms)*2 정도 쓰니 대략 1초 주기 맞춤
}
