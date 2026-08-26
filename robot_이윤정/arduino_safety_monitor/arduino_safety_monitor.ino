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
       얼굴이 계속 같은 모양이라 밋밋하다는 피드백으로, 처음엔 "^_^"/"-_-"
       텍스트로 눈 깜빡임을 넣었다가, 더 자연스럽게 보이도록 createChar()로
       5x8 픽셀 눈 모양(뜬눈/반쯤감김/감음 3단계) 커스텀 문자를 직접 만들어
       교체함 — RoboEyes 같은 그래픽 라이브러리는 OLED 전용이라 LCD1602엔
       못 쓰지만, HD44780 LCD도 8개까지 커스텀 문자를 만들 수 있어서 이
       방식으로 비슷한 효과를 냄.
  8차: "옆도 보는 모션" 추가 요청 — 눈 모양 자체(픽셀)를 좌우로 다르게
       그리는 대신, 두 눈 문자를 표시하는 커서 위치를 좌우로 1칸씩
       옮겼다가 되돌리는 방식으로 "곁눈질" 느낌을 구현함(간단하면서도
       16x2 화면에서 눈에 띄게 보임).
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);  // 주소, 컬럼 수, 행 수

// 커스텀 문자(5x8 픽셀) — 눈 모양 3단계. HD44780 LCD는 최대 8개까지
// 만들 수 있는데, 여기선 3개만 쓴다. 두 눈 다 같은 문자를 재사용한다
// (좌우 눈이 따로 움직이지 않고 항상 같이 뜨고/감기니까 그걸로 충분함).
const int EYE_OPEN = 0;
const int EYE_HALF = 1;
const int EYE_CLOSED = 2;

byte eyeOpenBitmap[8] = {
  B00000,
  B01110,
  B11111,
  B11111,
  B11111,
  B11111,
  B01110,
  B00000,
};
byte eyeHalfBitmap[8] = {
  B00000,
  B00000,
  B01110,
  B11111,
  B11111,
  B01110,
  B00000,
  B00000,
};
byte eyeClosedBitmap[8] = {
  B00000,
  B00000,
  B00000,
  B00000,
  B11111,
  B00000,
  B00000,
  B00000,
};

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
int lastEyeFrame = -1;  // 평온한 얼굴일 때만 쓰는 눈 애니메이션 프레임(0/1/2)
int lastEyeOffset = 0;  // 눈 커서 위치 좌우 오프셋(-1=왼쪽, 0=중앙, 1=오른쪽)
int frameCounter = 0;   // loop() 한 바퀴마다 증가 — 대략 1초에 1씩 늘어남

// 애니메이션 한 바퀴(대략 초 단위) 길이. 이 안에서 눈 깜빡임 한 번,
// 좌우 곁눈질 한 번씩 섞어서 보여준다.
const int ANIM_CYCLE_LEN = 16;

void setup() {
  Serial.begin(9600);
  pinMode(SOUND_PIN, INPUT);

  lcd.init();
  lcd.backlight();
  lcd.createChar(EYE_OPEN, eyeOpenBitmap);
  lcd.createChar(EYE_HALF, eyeHalfBitmap);
  lcd.createChar(EYE_CLOSED, eyeClosedBitmap);
  showFace(FACE_NORMAL, true, EYE_OPEN, 0);  // 시작하자마자 평온한(눈 뜬, 중앙) 얼굴부터 표시
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

// force가 true면 상태가 안 바뀌었어도 강제로 다시 그린다(초기 표시용).
// eyeFrame/eyeOffset은 FACE_NORMAL일 때만 의미 있음.
// eyeOffset: -1=왼쪽을 봄, 0=정면, 1=오른쪽을 봄 (커서 위치를 옮겨서 표현)
void showFace(Face face, bool force, int eyeFrame, int eyeOffset) {
  // 얼굴 종류/눈 프레임/좌우 오프셋 중 하나라도 바뀌었을 때만 다시 그린다
  // (매초 다시 그리면 화면이 깜빡거려서, 실제로 바뀔 때만 그림).
  if (face == lastFace && eyeFrame == lastEyeFrame && eyeOffset == lastEyeOffset && !force) return;
  lastFace = face;
  lastEyeFrame = eyeFrame;
  lastEyeOffset = eyeOffset;

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
      // 커스텀 픽셀 눈 두 개(같은 문자 재사용, 좌우 같이 깜빡이고 같이 곁눈질함)
      lcd.setCursor(6 + eyeOffset, 0);
      lcd.write(byte(eyeFrame));
      lcd.setCursor(9 + eyeOffset, 0);
      lcd.write(byte(eyeFrame));
      lcd.setCursor(3, 1);
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
    showFace(FACE_FIRE, false, 0, 0);
  } else if (sound) {
    showFace(FACE_LOUD, false, 0, 0);
  } else {
    // 평온한 상태일 때만 주기적으로 눈을 깜빡이거나 좌우를 살짝 봐서
    // 살아있는 느낌을 준다. ANIM_CYCLE_LEN(대략 16초) 한 바퀴 안에
    // 깜빡임 한 번, 왼쪽 곁눈질 한 번, 오른쪽 곁눈질 한 번을 섞는다.
    int pos = frameCounter % ANIM_CYCLE_LEN;
    int eyeFrame = EYE_OPEN;
    int eyeOffset = 0;

    if (pos == 6) {
      eyeFrame = EYE_HALF;                 // 깜빡이기 시작
    } else if (pos == 7) {
      eyeFrame = EYE_CLOSED;               // 완전히 감음
    } else if (pos == 11 || pos == 12) {
      eyeOffset = -1;                      // 왼쪽을 살짝 봄
    } else if (pos == 14 || pos == 15) {
      eyeOffset = 1;                       // 오른쪽을 살짝 봄
    }
    showFace(FACE_NORMAL, false, eyeFrame, eyeOffset);
  }
  frameCounter++;

  delay(900);  // readAverage()가 이미 (10*5=50ms)*2 정도 쓰니 대략 1초 주기 맞춤
}
