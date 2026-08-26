/*
  arduino_safety_monitor.ino — LostPatrol 안전센서(FLAME + LM35DZ + 소음센서)
  + LCD1602(I2C) 로봇 얼굴 표시

  FLAME/온도/소음 값을 1초에 한 줄씩 JSON으로 시리얼 출력한다.
  Raspberry Pi의 robot_이윤정/mock_controller/safety_monitor.py가 이 형식을
  그대로 읽는다 (docs/HARDWARE_REFERENCE.md의 제안 프로토콜과 동일):
      {"flame": 0, "temp_c": 26.4, "sound": 0}

  배선 (실제 연결 기준, 2026.08.26):
    FLAME 센서(2다리 포토트랜지스터형) 짧은다리→5V, 긴다리→A0 + 10kΩ 저항 거쳐 GND
    소음센서 모듈(비교기 내장, DO 있음)  +→5V, G→GND, DO→A2
    LM35DZ (평평한 면 기준 왼쪽부터)     왼쪽(VCC)→5V, 가운데(OUT)→A1, 오른쪽(GND)→GND
    LCD1602 I2C 모듈                    VCC→5V, GND→GND, SDA→A4, SCL→A5
      (I2C 주소는 스캐너로 확인, 0x27 — i2c_scanner/i2c_scanner.ino 참고)

  라이브러리: Arduino IDE 라이브러리 관리자에서 "LiquidCrystal I2C" 설치 필요.

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
  6차: LCD1602(I2C) 로봇 얼굴 표시 추가 — flame/sound 상태에 따라 평온한
       얼굴/놀란 얼굴로 전환. I2C 주소는 스캐너로 0x27 확인.
  7차: 대비 트리머가 뻑뻑해서 잘 안 돌아갔으나 칼로 돌려서 해결. 평온한
       얼굴이 계속 같은 모양이라 밋밋하다는 피드백으로, 눈 깜빡임
       애니메이션 추가(약 6초에 한 번씩 "^_^" → "-_-" → 다시 "^_^").
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);  // 주소, 컬럼 수, 행 수

const int FLAME_PIN = A0;  // 아날로그로 읽음 (포토트랜지스터+저항 회로)
const int SOUND_PIN = A2;  // 디지털로 읽음 (DO, 트리머로 감도 캘리브레이션 완료)
const int TEMP_PIN = A1;   // 아날로그 (LM35DZ)

// 실물 테스트로 확정(2026.08.26) — 라이터 반응 시 LED 켜지는 것까지 확인.
const int FLAME_THRESHOLD = 5;

const int SAMPLE_COUNT = 10;   // 평균낼 샘플 개수
const int SAMPLE_DELAY_MS = 5; // 샘플 사이 간격

// 얼굴 상태가 바뀔 때만 LCD를 다시 그린다 (매초 다시 그리면 화면이 깜빡임).
enum Face { FACE_NORMAL, FACE_FIRE, FACE_LOUD };
Face lastFace = FACE_NORMAL;
int lastBlink = -1;   // 평온한 얼굴일 때만 쓰는 애니메이션 프레임 (0=뜸, 1=깜빡임)
int frameCounter = 0; // loop() 한 바퀴마다 증가 — 대략 1초에 1씩 늘어남

const int BLINK_EVERY_N_FRAMES = 6;  // 약 6초에 한 번씩 눈 깜빡

void setup() {
  Serial.begin(9600);
  pinMode(SOUND_PIN, INPUT);

  lcd.init();
  lcd.backlight();
  showFace(FACE_NORMAL, true, 0);  // 시작하자마자 평온한 얼굴부터 표시
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

// 16x2 LCD라 커스텀 문자 없이 텍스트만으로 표정을 표현한다.
// force가 true면 상태가 안 바뀌었어도 강제로 다시 그린다(초기 표시용).
// blink는 FACE_NORMAL일 때만 의미 있음(0=눈 뜸, 1=눈 깜빡).
void showFace(Face face, bool force, int blink) {
  // 얼굴 종류나 깜빡임 프레임 둘 중 하나라도 바뀌었을 때만 다시 그린다
  // (매초 다시 그리면 화면이 깜빡거려서, 실제로 바뀔 때만 그림).
  if (face == lastFace && blink == lastBlink && !force) return;
  lastFace = face;
  lastBlink = blink;

  lcd.clear();
  switch (face) {
    case FACE_FIRE:
      lcd.setCursor(4, 0);
      lcd.print(">_< !!");
      lcd.setCursor(1, 1);
      lcd.print("FIRE DETECTED");
      break;
    case FACE_LOUD:
      lcd.setCursor(5, 0);
      lcd.print("O_O");
      lcd.setCursor(2, 1);
      lcd.print("LOUD SOUND!");
      break;
    case FACE_NORMAL:
    default:
      lcd.setCursor(6, 0);
      lcd.print(blink ? "-_-" : "^_^");  // 깜빡이는 순간만 눈 감은 모양으로
      lcd.setCursor(2, 1);
      lcd.print("LostPatrol");
      break;
  }
}

void loop() {
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
  if (flame) {
    showFace(FACE_FIRE, false, 0);
  } else if (sound) {
    showFace(FACE_LOUD, false, 0);
  } else {
    // 평온한 상태일 때만 몇 초에 한 번씩 눈을 깜빡여서 살아있는 느낌을 준다.
    int blink = (frameCounter % BLINK_EVERY_N_FRAMES == 0) ? 1 : 0;
    showFace(FACE_NORMAL, false, blink);
  }
  frameCounter++;

  delay(900);  // readAverage()가 이미 (10*5=50ms)*2 정도 쓰니 대략 1초 주기 맞춤
}
