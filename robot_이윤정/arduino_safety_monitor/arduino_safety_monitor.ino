/*
  arduino_safety_monitor.ino — LostPatrol 안전센서(FLAME + LM35DZ + 소음센서)

  FLAME/온도/소음 값을 1초에 한 줄씩 JSON으로 시리얼 출력한다.
  Raspberry Pi의 robot_이윤정/mock_controller/safety_monitor.py가 이 형식을
  그대로 읽는다 (docs/HARDWARE_REFERENCE.md의 제안 프로토콜과 동일):
      {"flame": 0, "temp_c": 26.4, "sound": 0}

  배선 (Arduino Uno/Nano 기준):
    FLAME 모듈   VCC→5V, GND→GND, DO→디지털 2번
    소음센서 모듈 VCC→5V, GND→GND, DO→디지털 3번
    LM35DZ       VCC→5V, GND→GND, OUT→아날로그 A0

  주의: 대부분의 IR 불꽃센서 모듈은 불꽃 감지 시 DO가 LOW로 떨어진다.
  실제로 업로드해서 시리얼 모니터로 확인했을 때 반대로 동작하면(평소 0,
  불꽃 대면 1이 아니라 그 반대라면) 아래 flame 계산의 "== LOW"를
  "== HIGH"로 바꾸면 된다. 소음센서도 모듈마다 HIGH/LOW 기준이 다를 수
  있으니 마찬가지로 확인 후 필요하면 바꿀 것.
*/

const int FLAME_PIN = 2;   // 디지털
const int SOUND_PIN = 3;   // 디지털
const int TEMP_PIN = A0;   // 아날로그 (LM35DZ)

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
