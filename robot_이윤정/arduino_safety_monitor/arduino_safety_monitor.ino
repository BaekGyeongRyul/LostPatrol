/*
  arduino_safety_monitor.ino — LostPatrol 안전센서(FLAME + LM35DZ + 소음센서)

  FLAME/온도/소음 값을 1초에 한 줄씩 JSON으로 시리얼 출력한다.
  Raspberry Pi의 robot_이윤정/mock_controller/safety_monitor.py가 이 형식을
  그대로 읽는다 (docs/HARDWARE_REFERENCE.md의 제안 프로토콜과 동일):
      {"flame": 0, "temp_c": 26.4, "sound": 0}

  배선 (실제 연결 기준, 2026.08.26):
    FLAME 모듈   VCC→5V, GND→GND, DO→A0
    소음센서 모듈 VCC→5V, GND→GND, DO→A2
    LM35DZ       VCC→5V, GND→GND, OUT→A1

  참고: A0~A5는 아날로그 전용이 아니라 digitalRead()/digitalWrite()도 그대로
  지원하는 핀이라, FLAME/소음센서의 디지털 출력(DO)을 여기 연결해도 문제없다.
  (첫 실물 테스트에서 소음/LM35DZ 핀이 코드와 반대로 배선돼있어서 temp_c가
  항상 499.5(ADC 최댓값)로, sound가 항상 0으로 고정되는 증상이 있었음 —
  소음센서의 디지털 HIGH를 온도핀이 읽고, LM35DZ의 낮은 아날로그 전압을
  소음핀이 읽어서 생긴 문제. 아래 핀 번호를 실제 배선에 맞게 수정함.)

  주의: 대부분의 IR 불꽃센서 모듈은 불꽃 감지 시 DO가 LOW로 떨어진다.
  실제로 업로드해서 시리얼 모니터로 확인했을 때 반대로 동작하면(평소 0,
  불꽃 대면 1이 아니라 그 반대라면) 아래 flame 계산의 "== LOW"를
  "== HIGH"로 바꾸면 된다. 소음센서도 모듈마다 HIGH/LOW 기준이 다를 수
  있으니 마찬가지로 확인 후 필요하면 바꿀 것.
*/

const int FLAME_PIN = A0;  // 디지털로 읽음 (DO)
const int SOUND_PIN = A2;  // 디지털로 읽음 (DO)
const int TEMP_PIN = A1;   // 아날로그 (LM35DZ)

void setup() {
  Serial.begin(9600);
  pinMode(FLAME_PIN, INPUT);
  pinMode(SOUND_PIN, INPUT);
}

void loop() {
  int flameRaw = digitalRead(FLAME_PIN);
  int soundRaw = digitalRead(SOUND_PIN);
  int tempRaw = analogRead(TEMP_PIN);

  int flame = (flameRaw == LOW) ? 1 : 0;   // 반대로 동작하면 HIGH로 바꿀 것
  int sound = (soundRaw == HIGH) ? 1 : 0;  // 반대로 동작하면 LOW로 바꿀 것

  // LM35DZ: 10mV/°C, Arduino 5V 기준전압 기준 변환 공식
  float tempC = (tempRaw * 5.0 / 1024.0) * 100.0;

  Serial.print("{\"flame\": ");
  Serial.print(flame);
  Serial.print(", \"temp_c\": ");
  Serial.print(tempC, 1);
  Serial.print(", \"sound\": ");
  Serial.print(sound);
  Serial.println("}");

  delay(1000);
}
