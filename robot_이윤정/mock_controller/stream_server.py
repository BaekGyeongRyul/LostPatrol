"""
stream_server.py — 라즈베리파이 카메라를 실시간 MJPEG로 웹에 스트리밍한다.

`rpicam-vid`로 영상을 계속 받아서(controller.py의 촬영 설정과 동일하게
rotation 180 / awb daylight 적용), HTTP로 MJPEG 스트림을 내보낸다.
브라우저는 그냥 <img src="http://<Pi IP>:8090/stream.mjpg"> 태그 하나로
실시간 영상을 볼 수 있다 (별도 플레이어/코덱 필요 없음 — 웹 브라우저가
multipart/x-mixed-replace를 기본으로 지원함).

`web_백경률/src/components/LiveCameraView.jsx`가 이미 `streamUrl` prop
하나만 받으면 되도록 만들어져 있어서, 이 서버의 URL을 그 prop에 넣어주면
그대로 연결된다 (Supabase 스키마 변경 없이 웹 쪽 config/코드에서 하드코딩
하거나, 나중에 팀 협의로 robot_status에 stream_url 컬럼을 추가해도 됨 —
새 컬럼 추가는 혼자 결정하지 않기로 한 팀 규칙 때문에 지금은 컬럼 추가는
하지 않음, docs/02_SUPABASE_DATA_CONTRACT.md 참고).

실행 (라즈베리파이에서만 동작 — rpicam-vid가 있어야 함):
    python3 stream_server.py
    → http://<Pi IP>:8090/stream.mjpg 로 접속해서 확인

엔드포인트 3개:
    /stream.mjpg     — 실시간 MJPEG 스트림 (브라우저용)
    /snapshot.jpg    — 지금 스트리밍 중인 프레임 한 장 재사용(저해상도,
                       카메라 재오픈 없이 빠름 — controller.py의 일반 촬영용)
    /hq_snapshot.jpg — 스트리밍을 잠깐 멈추고 고해상도(1296x972)로 한 장
                       직접 촬영 후 재개 (controller.py의 분실물 등록용
                       촬영처럼 화질이 중요할 때 씀, request_hq_capture() 참고)

CSI 카메라는 한 번에 한 프로세스만 열 수 있어서, rpicam-vid(이 서버)가
떠있는 채로 별도 rpicam-still을 그냥 열면 화면이 순간적으로 깨진다
(2026.08.30 확인) — 그래서 고해상도가 필요하면 /snapshot.jpg가 아니라
반드시 /hq_snapshot.jpg를 통해 이 서버 안에서 조율해서 찍어야 한다.
"""

import os
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RPICAM_VID = shutil.which("rpicam-vid")
RPICAM_STILL = shutil.which("rpicam-still")

STREAM_PORT = int(os.environ.get("STREAM_PORT", "8090"))
STREAM_WIDTH = int(os.environ.get("STREAM_WIDTH", "640"))
STREAM_HEIGHT = int(os.environ.get("STREAM_HEIGHT", "480"))
STREAM_FRAMERATE = int(os.environ.get("STREAM_FRAMERATE", "15"))

# 분실물 등록용 고해상도 촬영(/hq_snapshot.jpg) 중에는 스트리밍용
# rpicam-vid를 잠깐 내려야 한다(카메라는 한 번에 한 프로세스만 열 수
# 있음) — 이 두 이벤트로 캡처 루프 스레드와 신호를 주고받는다.
_pause_event = threading.Event()   # set: 캡처 루프가 rpicam-vid를 내려야 함
_paused_ack = threading.Event()    # set: 캡처 루프가 실제로 rpicam-vid를 내림


class FrameBroadcaster:
    """캡처 스레드가 채워넣은 최신 프레임을, 접속한 모든 클라이언트가
    같이 읽어가는 아주 단순한 브로드캐스터. 프레임 캡처와 HTTP 응답을
    분리해서, 여러 명이 동시에 봐도 rpicam-vid는 하나만 떠 있으면 된다."""

    def __init__(self):
        self._frame = None
        self._condition = threading.Condition()

    def set_frame(self, jpg_bytes: bytes) -> None:
        with self._condition:
            self._frame = jpg_bytes
            self._condition.notify_all()

    def get_frame(self) -> bytes:
        with self._condition:
            self._condition.wait()
            return self._frame


broadcaster = FrameBroadcaster()


def _run_vid_once() -> None:
    """rpicam-vid를 한 번 띄워서, 멈춤 요청(_pause_event)이 오거나
    프로세스가 죽을 때까지 프레임을 broadcaster에 계속 채워 넣는다."""
    cmd = [
        RPICAM_VID, "--codec", "mjpeg", "-o", "-", "-t", "0", "-n",
        # rpicam-still은 --rotation 180으로 잘 뒤집히는데, rpicam-vid는
        # 이 카메라(ov5647)의 저해상도 비디오 모드에서 --rotation이
        # 제대로 안 먹어서 화면이 위아래 반전된 채로 나오는 문제가 있었음
        # (2026.08.29). --hflip/--vflip을 대신 쓰면(180도 회전과 결과는
        # 같음) 이 비디오 모드에서도 정상 동작해서 이걸로 바꿈.
        "--hflip", "1", "--vflip", "1", "--awb", "daylight",
        "--width", str(STREAM_WIDTH), "--height", str(STREAM_HEIGHT),
        "--framerate", str(STREAM_FRAMERATE),
    ]
    print(f"[STREAM] rpicam-vid 시작: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    buf = b""
    try:
        while not _pause_event.is_set():
            chunk = proc.stdout.read(4096)
            if not chunk:
                print("[STREAM] rpicam-vid 출력 종료됨")
                break
            buf += chunk

            start = buf.find(b"\xff\xd8")  # JPEG 시작(SOI) 마커
            end = buf.find(b"\xff\xd9")    # JPEG 끝(EOI) 마커
            if start != -1 and end != -1 and end > start:
                jpg = buf[start:end + 2]
                buf = buf[end + 2:]
                broadcaster.set_frame(jpg)
    finally:
        proc.terminate()
        proc.wait()


def _capture_loop() -> None:
    """_run_vid_once()를 계속 반복 — 고해상도 촬영 요청(_pause_event)이
    오면 rpicam-vid를 내리고 대기했다가, 요청이 끝나면(_pause_event
    clear) 다시 새로 띄워서 스트리밍을 재개한다."""
    while True:
        if _pause_event.is_set():
            _paused_ack.set()  # "지금 rpicam-vid 꺼져있음" 확인 신호
            time.sleep(0.05)
            continue
        _paused_ack.clear()
        _run_vid_once()


def request_hq_capture(timeout: float = 15):
    """스트리밍(rpicam-vid)을 잠깐 멈추고 고해상도 사진 한 장을 rpicam-still로
    직접 찍은 뒤, 스트리밍을 다시 재개한다. 실패하면 None.

    카메라는 한 번에 한 프로세스만 열 수 있어서, rpicam-vid가 떠있는 채로
    rpicam-still을 또 열면 화면이 순간적으로 깨지는 문제가 있었다
    (2026.08.30) — 분실물 등록용 사진은 화질이 중요한데 스트리밍용
    저해상도(640x480) 프레임 재사용은 YOLO 인식률이 떨어져서, 이렇게
    "잠깐 스트리밍 끄고 고해상도로 찍고 다시 켜기" 방식으로 바꿈.
    """
    if RPICAM_STILL is None:
        return None
    _pause_event.set()
    if not _paused_ack.wait(timeout=2):
        print("[STREAM] rpicam-vid 정지 확인 타임아웃 — 그래도 촬영 시도")
    try:
        result = subprocess.run(
            [RPICAM_STILL, "-o", "-", "-t", "1000", "-n",
             "--rotation", "180", "--awb", "daylight",
             "--width", "1296", "--height", "972"],
            capture_output=True, timeout=timeout, check=True,
        )
        return result.stdout
    except Exception as exc:
        print(f"[STREAM] 고해상도 촬영 실패: {exc}")
        return None
    finally:
        _pause_event.clear()  # 캡처 루프가 rpicam-vid를 다시 띄우게 함


class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/snapshot.jpg":
            self._serve_snapshot()
            return
        if self.path == "/hq_snapshot.jpg":
            self._serve_hq_snapshot()
            return
        if self.path != "/stream.mjpg":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=FRAME")
        self.end_headers()

        try:
            while True:
                frame = broadcaster.get_frame()
                self.wfile.write(b"--FRAME\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError):
            pass  # 클라이언트가 페이지를 닫음 — 정상 상황, 조용히 넘어감

    def _serve_snapshot(self) -> None:
        """지금 스트리밍 중인 최신 프레임 한 장을 그냥 JPEG 이미지로 돌려준다.

        controller.py의 capture 명령이 카메라를 따로 열지 않고 이 주소를
        통해 프레임을 가져다 쓸 수 있게 하기 위함 — rpicam-vid(스트리밍)와
        rpicam-still(캡처)이 카메라를 동시에 열면 충돌할 수 있어서, 스트리밍
        서버가 떠있을 땐 이미 찍고 있는 영상에서 프레임을 재사용하는 방식으로
        충돌을 피한다(2026.08.27, 실시간 화면 보면서 캡처도 하고 싶다는
        요청으로 추가).
        """
        frame = broadcaster.get_frame()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(frame)))
        self.end_headers()
        self.wfile.write(frame)

    def _serve_hq_snapshot(self) -> None:
        """스트리밍을 잠깐 멈추고 고해상도 사진 한 장을 찍어서 돌려준다.

        controller.py가 분실물 등록용 사진을 찍을 때 이 주소를 쓴다
        (2026.08.30) — /snapshot.jpg(스트리밍 프레임 재사용)는 화질이
        낮아서 YOLO 인식률이 떨어지는 문제가 있었음. request_hq_capture()
        참고.
        """
        data = request_hq_capture()
        if data is None:
            self.send_response(503)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # 매 프레임마다 접속 로그 찍히면 시끄러워서 끔


def run() -> None:
    if not RPICAM_VID:
        print("[STREAM] rpicam-vid를 찾을 수 없습니다 — 이 스크립트는 실물 라즈베리파이에서만 동작합니다.")
        return

    threading.Thread(target=_capture_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", STREAM_PORT), StreamHandler)
    print(f"[STREAM] http://<Pi IP>:{STREAM_PORT}/stream.mjpg 에서 스트리밍 시작")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STREAM] 종료합니다.")


if __name__ == "__main__":
    run()
