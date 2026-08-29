/*
  arduino_safety_monitor.ino — LostPatrol 안전센서(FLAME + LM35DZ + 소음센서)
  + LCD1602(I2C, 텍스트 상태 표시) + ESP32로 보내는 flame/sound 신호 핀

  FLAME/온도/소음 값을 1초에 한 줄씩 JSON으로 시리얼 출력한다.
  Raspberry Pi의 robot_이윤정/mock_controller/safety_monitor.py가 이 형식을
  그대로 읽는다 (docs/HARDWARE_REFERENCE.md의 제안 프로토콜과 동일):
      {"flame": 0, "temp_c": 26.4, "sound": 0}

  배선 (실제 연결 기준, 2026.08.26~27):
    FLAME 센서(2다리 포토트랜지스터형) 짧은다리→5V, 긴다리→A0 + 10kΩ 저항 거쳐 GND
    소음센서 모듈(KY-038, 비교기+마이크) +→5V, G→GND, A0→우노 A2
      (D0/트리머 기반 판정은 감도 구간이 너무 좁아서(항상 꺼짐 ↔ 항상 켜짐
      둘 중 하나로만 튐) 2026.08.29에 포기하고, FLAME과 같은 방식으로
      아날로그 원본(A0)을 코드에서 임계값 비교하는 걸로 바꿈 — 아래 14차 참고)
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
       읽기를 빼고 고정값을 보내도록 임시 조치했다가, 2026.08.29 아예
       온도 기능 자체를 뺌(LCD 표시도 제거) — 센서 수리/교체 후 다시 넣을 것.
       JSON에는 프로토콜 호환을 위해 temp_c:0.0으로 계속 보냄(안 쓰는 값).
  13차: 웹사이트가 화재 감지 후에도 계속 normal로 뜨는 문제 발생(2026.08.29)
       → 우노/LCD는 정상(FIRE로 잘 바뀜)인데 safety_monitor.py가
       "/dev/ttyACM0: No such file or directory" 에러로 mock 모드로
       빠져있었음. USB 재연결로 포트가 ttyACM1로 바뀐 게 원인 — .env의
       SERIAL_PORT를 갱신하고 safety_monitor.py 재시작해서 해결. (USB
       재연결/재부팅마다 ttyACM 번호가 바뀔 수 있다는 점 기억할 것.)
  14차: 소음센서(KY-038) D0+트리머 방식이 "박수 쳐도 전혀 반응 없음"과
       "평소에도 계속 반응"사이의 중간 지점을 트리머로 못 찾음(2026.08.29)
       — 트리머 감도 구간이 너무 좁은 걸로 추정. FLAME과 동일하게
       아날로그 원본(A0)을 우노 SOUND_ANALOG_PIN(A2)으로 읽어서 코드에서
       직접 임계값(SOUND_THRESHOLD) 비교하는 방식으로 변경. 초기값은
       미측정 상태라 임시로 넉넉하게 잡아둠 — 실측 후 FLAME_THRESHOLD처럼
       평소값/박수값 사이로 재조정 필요(SOUND_THRESHOLD 옆 주석 참고).
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);  // 주소, 컬럼 수, 행 수

const int FLAME_PIN = A0;  // 아날로그로 읽음 (포토트랜지스터+저항 회로)

// 소음센서(KY-038)의 A0(아날로그 원본)를 읽음 — 2026.08.29, D0+트리머 방식
// 대신 FLAME과 같은 "아날로그 읽고 코드에서 임계값 비교" 방식으로 변경.
const int SOUND_ANALOG_PIN = A2;

// LM35DZ 다리가 부러져서(2026.08.27) 온도 기능 자체를 뺌(2026.08.29).
// JSON 프로토콜 호환을 위해 temp_c는 계속 0.0으로 보내되, fire 판정은
// flame 센서만으로 함. 센서 교체/수리되면 TEMP_PIN 살리고
// readAverage(TEMP_PIN) 다시 쓰면 됨.

// ESP32로 flame/sound 판정 결과를 그대로 내보내는 디지털 출력 핀.
// ESP32는 이 두 핀만 읽어서 얼굴 표정을 결정한다 — 별도 프로토콜 없이
// 그냥 HIGH/LOW 신호만 주고받는 가장 단순한 방식.
const int FLAME_OUT_PIN = 8;
const int SOUND_OUT_PIN = 9;

// 화재 감지 시 켜지는 빨간 LED. 긴다리(+)→D7, 짧은다리(-)→GND
// (사이에 220~330Ω 저항 있으면 같이 연결) — 2026.08.29 D2는 소음센서로 넘겨줌
const int FIRE_LED_PIN = 7;

// 큰 소리 감지 시 켜지는 LED. 긴다리(+)→D13, 짧은다리(-)→GND
const int SOUND_LED_PIN = 13;

// 2026.08.26엔 5로 확정했었으나, 2026.08.29 재측정 결과 평소값 0~2,
// 실제 불꽃 반응 시 1023(ADC 최댓값)으로 나와서 5는 너무 타이트했음
// (전원(배터리/USB) 종류에 따라 잡음 몇 카운트 차이로도 오작동하는 원인이 됨).
// 여유 있게 100으로 올림 — 평소값보다는 훨씬 높고, 실제 불꽃 값(1023)보다는
// 훨씬 낮아서 노이즈에 안정적임.
const int FLAME_THRESHOLD = 100;

// 미측정 상태의 임시값(2026.08.29) — 업로드 후 Serial Monitor에서
// "DEBUG soundRaw=" 값을 평소(조용할 때)/박수 칠 때 각각 확인해서,
// FLAME_THRESHOLD 했던 것처럼 그 사이 넉넉한 값으로 바꿔줄 것.
const int SOUND_THRESHOLD = 500;

const int SAMPLE_COUNT = 10;   // 평균낼 샘플 개수
const int SAMPLE_DELAY_MS = 5; // 샘플 사이 간격

enum Mood { MOOD_NORMAL, MOOD_FIRE, MOOD_LOUD };
Mood lastLcdMood = MOOD_NORMAL;  // LCD는 값이 바뀔 때만 다시 그려서 깜빡임 방지

void setup() {
  Serial.begin(9600);
  // SOUND_ANALOG_PIN(A2)은 analogRead()로만 쓰므로 pinMode 설정 불필요.
  pinMode(FLAME_OUT_PIN, OUTPUT);
  pinMode(SOUND_OUT_PIN, OUTPUT);
  pinMode(FIRE_LED_PIN, OUTPUT);
  pinMode(SOUND_LED_PIN, OUTPUT);
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

void updateLcd(Mood mood) {
  if (mood == lastLcdMood) return;  // 상태 그대로면 다시 그리지 않음(깜빡임 방지)
  lastLcdMood = mood;

  // 화재 시에는 급박한 느낌을 위해 "LostPatrol" 대신 경고 문구로 화면 전체를 씀
  // (LCD1602는 한글 표시가 안 돼서 영어로 작성)
  if (mood == MOOD_FIRE) {
    lcd.setCursor(0, 0);
    lcd.print("!!!  FIRE!  !!! ");
    lcd.setCursor(0, 1);
    lcd.print("Send Help Now!  ");
    return;
  }

  lcd.setCursor(0, 0);
  lcd.print("LostPatrol      ");

  lcd.setCursor(0, 1);
  switch (mood) {
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
  int soundRaw = readAverage(SOUND_ANALOG_PIN);

  int flame = (flameRaw > FLAME_THRESHOLD) ? 1 : 0;
  int sound = (soundRaw > SOUND_THRESHOLD) ? 1 : 0;

  Serial.print("DEBUG soundRaw=");  // 임시 디버그 — SOUND_THRESHOLD 재조정 끝나면 지울 것
  Serial.println(soundRaw);

  Serial.print("{\"flame\": ");
  Serial.print(flame);
  Serial.print(", \"temp_c\": 0.0");  // 온도 기능 뺌(LM35DZ 다리 파손) — 프로토콜 호환용 자리값
  Serial.print(", \"sound\": ");
  Serial.print(sound);
  Serial.println("}");

  // ESP32로 그대로 신호 전달
  digitalWrite(FLAME_OUT_PIN, flame ? HIGH : LOW);
  digitalWrite(SOUND_OUT_PIN, sound ? HIGH : LOW);

  // 화재 감지 시 빨간 LED, 큰 소리 감지 시 소음 LED 켜기
  digitalWrite(FIRE_LED_PIN, flame ? HIGH : LOW);
  digitalWrite(SOUND_LED_PIN, sound ? HIGH : LOW);

  // 우선순위: 불꽃 > 큰 소리 > 평온. (둘 다 감지되면 더 위험한 불꽃 표정 우선)
  Mood mood = MOOD_NORMAL;
  if (flame) {
    mood = MOOD_FIRE;
  } else if (sound) {
    mood = MOOD_LOUD;
  }

  updateLcd(mood);

  delay(900);  // readAverage()가 이미 (10*5=50ms)*2 정도 쓰니 대략 1초 주기 맞춤
}