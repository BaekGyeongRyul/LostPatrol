/*
  i2c_scanner.ino — LCD1602 I2C 모듈의 실제 I2C 주소를 찾기 위한 스캐너.

  LCD I2C 백팩(PCF8574 기반)은 제조사마다 주소가 0x27 또는 0x3F 등으로
  다르다. 이 스케치를 업로드하고 시리얼 모니터(9600 baud)를 열면 연결된
  I2C 장치의 주소를 알려준다. 주소 확인 후에는 다시 원래 용도(로봇 얼굴)
  스케치로 교체하면 된다.
*/

#include <Wire.h>

void setup() {
  Wire.begin();
  Serial.begin(9600);
  while (!Serial) {}
  Serial.println("I2C 스캔 시작...");
}

void loop() {
  byte error, address;
  int found = 0;

  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0) {
      Serial.print("I2C 장치 발견: 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
      found++;
    }
  }

  if (found == 0) {
    Serial.println("장치를 못 찾았습니다 — 배선(SDA/SCL/VCC/GND) 확인해주세요.");
  }

  delay(3000);
}
