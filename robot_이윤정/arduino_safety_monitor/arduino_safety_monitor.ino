/*
  arduino_safety_monitor.ino — LostPatrol 안전센서(FLAME + LM35DZ + 소음센서)

  FLAME/온도/소음 값을 1초에 한 줄씩 JSON으로 시리얼 출력한다.
  Raspberry Pi의 robot_이윤정/mock_controller/safety_monitor.py가 이 형식을
  그대로 읽는다 (docs/HARDWARE_REFERENCE.md의 제안 프로토콜과 동일):
      {"flame": 0, "temp_c": 26.4, "sound": 0}

  배선 (실제 연결 기준, 2026.08.26):
    FLAME 센서(2다리 포토트랜지스터형) 짧은다리→5V, 긴다리→A0 + 10kΩ 저항 거쳐 GND
    소음센서 모듈(비교기 내장, DO 있음)  +→5V, G→GND, DO→A2
    LM35DZ (평평한 면 기준 왼쪽부터)     왼쪽(VCC)→5V, 가운데(OUT)→A1, 오른쪽(GND)→GND

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
*/

const int FLAME_PIN = A0;  // 아날로그로 읽음 (포토트랜지스터+저항 회로)
const int SOUND_PIN = A2;  // 디지털로 읽음 (DO, 트리머로 감도 캘리브레이션 완료)
const int TEMP_PIN = A1;   // 아날로그 (LM35DZ)

// 실물 테스트로 확정(2026.08.26) — 라이터 반응 시 LED 켜지는 것까지 확인.
const int FLAME_THRESHOLD = 5;

const int SAMPLE_COUNT = 10;   // 평균낼 샘플 개수
const int SAMPLE_DELAY_MS = 5; // 샘플 사이 간격

void setup() {
  Serial.begin(9600);
  pinMode(SOUND_PIN, INPUT);
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

  delay(900);  // readAverage()가 이미 (10*5=50ms)*2 정도 쓰니 대략 1초 주기 맞춤
}
