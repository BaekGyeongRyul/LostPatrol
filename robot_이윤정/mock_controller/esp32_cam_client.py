"""
esp32_cam_client.py — XIAO ESP32S3 Sense(USB 시리얼 직결)에서 사진 한 장을
받아오는 헬퍼. Pi의 CSI 카메라(리본 케이블) 인식 문제(2026.08.27)의 백업
카메라로 사용.

프로토콜(esp32_camera_backup.ino와 짝):
    Pi -> ESP32: "CAPTURE\n"
    ESP32 -> Pi: 바이트 수(줄바꿈으로 끝나는 숫자 한 줄) + 그만큼의 JPEG 원본 바이트

단독 테스트:
    python3 esp32_cam_client.py /dev/ttyACM1 test.jpg
    (포트 번호는 `ls /dev/ttyACM* /dev/ttyUSB*`로 확인 — 아두이노 우노랑
    포트가 겹치지 않는지 확인할 것)
"""

import sys
import time

try:
    import serial
except ImportError:
    serial = None


def grab_frame_bytes(port: str, baud: int = 115200, timeout: float = 10) -> bytes:
    """ESP32 카메라 보드에서 JPEG 바이트를 받아온다. 실패 시 예외 발생."""
    if serial is None:
        raise RuntimeError("pyserial이 설치되어 있지 않습니다 (pip install pyserial)")

    ser = serial.Serial(port, baud, timeout=timeout)
    try:
        time.sleep(2)  # 보드가 시리얼 오픈 시 리셋되는 보드가 많아서 안정화 대기
        ser.reset_input_buffer()

        ser.write(b"CAPTURE\n")
        size_line = ser.readline().decode("ascii", errors="ignore").strip()
        if not size_line.isdigit():
            raise RuntimeError(f"크기 응답 이상함: {size_line!r}")
        size = int(size_line)
        if size == 0:
            raise RuntimeError("ESP32 쪽 촬영 실패(크기 0 응답)")

        data = ser.read(size)
        if len(data) != size:
            raise RuntimeError(f"수신 바이트 부족: {len(data)}/{size}")
        return data
    finally:
        ser.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python3 esp32_cam_client.py <포트> <저장할파일.jpg>")
        sys.exit(1)

    port, out_path = sys.argv[1], sys.argv[2]
    data = grab_frame_bytes(port)
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"저장 완료: {out_path} ({len(data)} bytes)")
