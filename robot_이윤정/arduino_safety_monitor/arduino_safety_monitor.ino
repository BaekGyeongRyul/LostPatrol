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
       고정됨. 이 회로는 밝을수록(IR 강할수록) A0 전압이 올라가는 구조라서
       analogRead()로 바꾸고 임계값(FLAME_THRESHOLD)과 비교하는 방식으로
       수정함. 정확한 임계값은 실측 후 조정 필요 — 평상시(불 없음) raw 값과
       불 켰을 때 raw 값을 시리얼로 확인해서 그 사이 값으로 맞추면 된다
       (아래 flame_raw를 JSON에 같이 출력해뒀으니 참고, 값 확정되면 지워도 됨).

  주의: 소음센서도 계속 1(또는 0)로 고정되면 모듈에 있는 트리머(가변저항)로
  감도를 조절해야 할 수 있다 (라인트레이싱 센서 캘리브레이션과 같은 원리).
*/

const int FLAME_PIN = A0;  // 아날로그로 읽음 (포토트랜지스터+저항 회로)
const int SOUND_PIN = A2;  // 디지털로 읽음 (DO, 비교기 내장 모듈)
const int TEMP_PIN = A1;   // 아날로그 (LM35DZ)

// TBD - 실측 후 조정. 평상시 raw 값보다 확실히 높고, 불 켰을 때 raw 값보다
// 낮은 중간값으로 맞추면 된다. 시리얼 모니터의 flame_raw를 보면서 조정.
const int FLAME_THRESHOLD = 500;

void setup() {
  Serial.begin(9600);
  pinMode(SOUND_PIN, INPUT);
}

void loop() {
  int flameRaw = analogRead(FLAME_PIN);
  int soundRaw = digitalRead(SOUND_PIN);
  int tempRaw = analogRead(TEMP_PIN);

  int flame = (flameRaw > FLAME_THRESHOLD) ? 1 : 0;
  int sound = (soundRaw == HIGH) ? 1 : 0;  // 계속 고정이면 트리머로 감도 조절 필요

  // LM35DZ: 10mV/°C, Arduino 5V 기준전압 기준 변환 공식
  float tempC = (tempRaw * 5.0 / 1024.0) * 100.0;

  Serial.print("{\"flame\": ");
  Serial.print(flame);
  Serial.print(", \"flame_raw\": ");   // 캘리브레이션용 — 임계값 확정되면 지워도 됨
  Serial.print(flameRaw);
  Serial.print(", \"temp_c\": ");
  Serial.print(tempC, 1);
  Serial.print(", \"sound\": ");
  Serial.print(sound);
  Serial.println("}");

  delay(1000);
}
