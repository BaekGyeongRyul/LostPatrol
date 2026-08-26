"""
safety_monitor.py — Arduino(FLAME + LM35DZ 온도센서 + 소음센서) 값을 읽어서
Supabase safety_status/patrol_events에 반영하는 독립 프로그램.

데이터 흐름 (웹 쪽 mockPatrolData.js 주석 기준):
    Arduino(FLAME + LM35DZ, Sound Sensor) → Raspberry Pi 5 → Supabase → Web

controller.py(모터/명령)와는 별개의 하드웨어(Arduino, USB 시리얼로 연결)를
다루는 별개의 프로그램이라 파일을 분리했다. 라즈베리파이에서는 이 스크립트와
controller.py를 각각 따로 실행하면 된다.

지금은 Arduino가 없어서(주문 중) SERIAL_PORT가 없거나 열리지 않으면 자동으로
그럴듯한 가짜 값을 생성하는 mock 모드로 동작한다 — Arduino 도착하면 .env에
SERIAL_PORT만 채워주면 코드 수정 없이 실물 모드로 전환된다.

Arduino 쪽에서 보내야 하는 시리얼 프로토콜 (9600 baud, 1초에 한 줄):
    {"flame": 0, "temp_c": 26.4, "sound": 0}
    - flame: 0/1 (불꽃 감지 여부)
    - temp_c: 섭씨 온도 (LM35DZ)
    - sound: 0/1 (큰 소리 감지 여부, 아두이노 쪽에서 임계값 판단 후 보내도 되고
      raw 값을 보내면 여기서 판단해도 됨 — 지금은 0/1로 가정)
"""

import json
import os
import random
import time

import store

try:
    import serial  # pyserial. 없어도 mock 모드는 동작해야 하므로 optional
except ImportError:
    serial = None

SERIAL_PORT = os.environ.get("SERIAL_PORT")  # 예: Windows "COM5", 라즈베리파이 "/dev/ttyUSB0"
SERIAL_BAUD = int(os.environ.get("SERIAL_BAUD", "9600"))

READ_INTERVAL_SEC = 2  # 이 주기로 센서 값을 읽어서 Supabase에 반영

# TBD - 팀 협의 후 확정. 실물 센서로 캘리브레이션 전까지의 자리표시자 값.
TEMPERATURE_WARNING_C = 40
TEMPERATURE_DANGER_C = 60

DEFAULT_LOCATION = "A구역"  # TBD - 실제 구역 라벨은 팀 협의 후 확정

# 이전 상태를 기억해서 "상태가 바뀔 때만" patrol_events에 기록한다
# (매번 기록하면 2초마다 로그가 쌓여서 이벤트 로그의 의미가 없어짐).
_last_flame = False
_last_sound = False


def _open_serial():
    if serial is None or not SERIAL_PORT:
        return None
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        # 포트를 열면 대부분의 아두이노 보드는 DTR 신호 때문에 자동으로
        # 리셋된다(재부팅). 리셋 직후 부트로더가 안정화되기 전까지 들어오는
        # 바이트는 쓰레기 값(널 바이트 등)일 수 있어서, 잠깐 기다렸다가
        # 그 사이 쌓인 입력 버퍼를 비우고 시작한다 (실물 테스트로 확인,
        # 2026.08.26 — 리셋 직후 계속 '\x00' 바이트만 읽히던 문제).
        time.sleep(2)
        ser.reset_input_buffer()
        return ser
    except Exception as exc:
        print(f"[SAFETY] 시리얼 포트({SERIAL_PORT}) 열기 실패, mock으로 전환: {exc}")
        return None


def _read_real(ser) -> dict:
    """Arduino가 보낸 한 줄(JSON)을 읽어서 파싱한다. 실패하면 None."""
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        print(f"[SAFETY] 시리얼 파싱 실패, 건너뜀: {line!r}")
        return None


def _read_mock() -> dict:
    """Arduino 없을 때 쓰는 가짜 값. 대부분 평상시 값이고 가끔 이벤트 발생."""
    flame = random.random() < 0.02  # 2% 확률로 불꽃 감지 흉내
    sound = random.random() < 0.05  # 5% 확률로 큰 소리 감지 흉내
    temp_c = round(25.0 + random.uniform(-1.5, 1.5), 1)
    if flame:
        temp_c += random.uniform(10, 30)  # 불꽃 감지 시 온도도 같이 튀게
    return {"flame": int(flame), "temp_c": round(temp_c, 1), "sound": int(sound)}


def _severity_for_fire(flame: bool, temp_c: float) -> str:
    if flame or temp_c >= TEMPERATURE_DANGER_C:
        return "danger"
    if temp_c >= TEMPERATURE_WARNING_C:
        return "warning"
    return "normal"


def _severity_for_sound(sound: bool) -> str:
    return "warning" if sound else "normal"


def _handle_reading(reading: dict) -> None:
    global _last_flame, _last_sound

    flame = bool(reading.get("flame"))
    temp_c = float(reading.get("temp_c", 0))
    sound = bool(reading.get("sound"))

    fire_severity = _severity_for_fire(flame, temp_c)
    sound_severity = _severity_for_sound(sound)

    store.update_safety_status(
        fire_severity=fire_severity,
        flame_detected=flame,
        temperature_c=temp_c,
        sound_severity=sound_severity,
        sound_level="high" if sound else "low",
    )
    print(f"[SAFETY] flame={flame} temp={temp_c}°C sound={sound} → fire={fire_severity} sound_sev={sound_severity}")

    # 상태가 "바뀐 순간"에만 이벤트를 기록한다 (연속 감지 중 매번 쌓이지 않게)
    if flame and not _last_flame:
        store.add_patrol_event("fire_detected", DEFAULT_LOCATION, "화재 의심 감지 (불꽃/고온)", "danger")
    if not flame and _last_flame:
        store.add_patrol_event("status_normal", DEFAULT_LOCATION, "화재 경보 해제", "normal")
    if sound and not _last_sound:
        store.add_patrol_event("loud_sound", DEFAULT_LOCATION, "큰 소리 감지", "warning")

    _last_flame, _last_sound = flame, sound


def run():
    store.init_store()
    ser = _open_serial()
    mode = "실물(시리얼)" if ser else "mock(가짜 값)"
    print(f"[SAFETY] 안전 감지 모니터 시작 — {mode} 모드, {READ_INTERVAL_SEC}초 주기")

    while True:
        try:
            reading = _read_real(ser) if ser else _read_mock()
            if reading:
                _handle_reading(reading)
        except Exception as exc:
            # 다른 프로그램들과 같은 원칙: 죽지 않고 로그만 남기고 계속 시도
            print(f"[SAFETY] 처리 중 오류(다음 주기에 재시도): {exc}")
        time.sleep(READ_INTERVAL_SEC)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n[SAFETY] 종료합니다.")
