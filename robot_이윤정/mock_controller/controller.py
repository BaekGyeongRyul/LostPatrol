"""
controller.py — 로봇 역할을 흉내내는 메인 루프 (지금은 "가짜" 로봇).

실제 라즈베리파이가 도착하면, 이 파일의 뼈대(명령 polling → 분기 →
상태 업데이트 → heartbeat → 순찰 루프)는 그대로 두고, _move()/_capture()/
_check_obstacle() 안쪽 내용만 Yahboom 모터 라이브러리·카메라·초음파센서
호출로 바꾸면 된다.

팀 계약(LostPatrol/docs/02_SUPABASE_DATA_CONTRACT.md,
YOONJEONG_RAZBOT_GUIDE.md) 기준으로 아래 규칙을 반영했다:
- command는 정확히 8종: forward/backward/left/right/stop/capture/
  patrol_start/patrol_stop ("buzz"는 계약에 없는 값 — 로컬 테스트용으로만
  남겨두고, 실제 Supabase로는 절대 보내지 않는다. RLS가 8종 외에는
  INSERT 자체를 막는다)
- left/right는 반드시 제자리 회전
- robot_status.updated_at은 5초마다 갱신(heartbeat), 웹은 15초 지나면
  OFFLINE 표시
- patrol_start/patrol_stop은 백그라운드 라인트레이싱 루프를 켜고 끄는
  토글이고, 수동 명령(특히 stop)이 오면 순찰보다 항상 우선해서 즉시 정지
- 에러 발생 시 로봇을 먼저 정지시키고 나서 로그를 남긴다 ("정지 우선")

실행:
    python controller.py
켜두고 다른 터미널에서 send_command.py로 명령을 넣어보면서 테스트한다.
"""

import time
import os
import shutil
import subprocess
import threading
import store

try:
    import winsound  # Windows 전용. 노트북에서 실제 "삑" 소리를 내기 위함.
except ImportError:
    winsound = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

# 실물 Razbot(라즈베리파이)에만 있는 CSI 카메라 촬영 커맨드라인 도구.
# 있으면 실물 카메라로, 없으면(노트북 등) 웹캠으로 자동 분기한다.
RPICAM_STILL = shutil.which("rpicam-still")

try:
    # 실물 로봇(라즈베리파이)에서만 import 성공한다 — I2C(smbus)가 있어야
    # 동작하는 라이브러리라 노트북(Windows)에서는 실패하는 게 정상이고,
    # 그 경우 아래 _car가 None으로 남아서 자동으로 mock(흉내) 모드로 돈다.
    import YB_Pcb_Car
    _car = YB_Pcb_Car.YB_Pcb_Car()
    print("[ROBOT] YB_Pcb_Car 로드 완료 — 실물 모터 제어 모드")
except Exception as exc:
    _car = None
    print(f"[ROBOT] YB_Pcb_Car 로드 실패({exc}) — mock 모터 모드로 동작")

# 초음파(Echo/Trig)·라인트레이싱 4채널 센서용. YB_Pcb_Car와 마찬가지로
# 실물 라즈베리파이에서만 성공하고, 노트북에서는 실패해서 None으로 남는다.
ECHO_PIN, TRIG_PIN = 18, 16  # BOARD 핀 번호 (HARDWARE_REFERENCE.md 참고)
TRACKING_LEFT1, TRACKING_LEFT2 = 13, 15
TRACKING_RIGHT1, TRACKING_RIGHT2 = 11, 7

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(TRACKING_LEFT1, GPIO.IN)
    GPIO.setup(TRACKING_LEFT2, GPIO.IN)
    GPIO.setup(TRACKING_RIGHT1, GPIO.IN)
    GPIO.setup(TRACKING_RIGHT2, GPIO.IN)
    print("[ROBOT] RPi.GPIO 초기화 완료 — 실물 초음파/라인트레이싱 모드")
except Exception as exc:
    GPIO = None
    print(f"[ROBOT] RPi.GPIO 로드 실패({exc}) — mock 센서 모드로 동작")

WEBCAM_INDEX = 0  # 노트북 기본 웹캠. 카메라가 여러 개면 1, 2...로 바꿔서 테스트

# 모터 속도, Yahboom 예제 기본값 그대로(0~255 범위)
MOVE_SPEED = 150

# 자동순찰 중 조향 속도는 MOVE_SPEED보다 낮게 — 실물 테스트에서 꺾을 때
# 너무 빨리 돌아서 라인을 넘어가버리고(오버슈트) 이탈하는 문제가 있어서
# 순찰 전용으로 더 느린 속도를 따로 둠(2026.08.27).
PATROL_SPEED = 80

# 시연 영상용 임시 모드 — True면 patrol_start가 실제 라인트레이싱 대신
# "앞으로 70cm → 우회전 → 앞으로 30cm" 고정 시퀀스를 수행한다(2026.08.27).
# 실제 라인트레이싱 코드는 그대로 아래에 남겨뒀으니, 시연 끝나면 False로
# 되돌리면 다시 원래대로 동작한다.
PATROL_DEMO_MODE = True

# 아래 세 값은 초 단위 추정치 — 실물로 보면서 cm/각도에 맞게 계속 조정 중.
# 1차: 2.0/0.6/1.0 → 실물로 60cm쪽으로 줄이고 싶다 + 0.6초로는 90도 부족
# 2차(2026.08.27): 60cm 비례로 줄이고, 회전 시간 늘림 — 더 필요하면 계속 조정.
DEMO_FORWARD1_SEC = 1.7   # 약 60cm
DEMO_TURN_SEC = 1.0       # 우회전 약 90도 (0.6초로는 부족했음, 늘림)
DEMO_FORWARD2_SEC = 1.0   # 약 30cm

# 이동 명령이 실제로 걸리는 시간(초). mock 모드에서는 흉내내는 sleep 시간으로,
# 실물 모드에서는 "이 시간만큼 움직이고 자동으로 멈춘다"는 의미로 쓰인다.
MOVE_DURATION_SEC = 1.5

# 제자리 회전(left/right)은 전진/후진보다 훨씬 짧게 돌아야 한다 — 실물
# 테스트 결과 1.5초면 거의 한 바퀴 넘게 돌아버려서, 조금씩만 돌도록 별도
# 값으로 분리했다. 필요하면 이 값만 조정하면 됨 (초 단위).
SPIN_DURATION_SEC = 0.3

# 팀 계약: robot_status.updated_at을 5초마다 갱신해야 함 (15초 지나면 웹이 OFFLINE 표시)
HEARTBEAT_INTERVAL_SEC = 5

# TBD - 팀 협의 후 확정. 초음파 센서 실물이 없어서 지금은 안 쓰이는 자리표시자 값.
OBSTACLE_STOP_DISTANCE_CM = 20

CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "data", "captures")

# 현재 상태를 메인 루프/heartbeat 스레드/순찰 스레드가 공유해서 참조한다.
_state_lock = threading.Lock()
_current_state = "idle"
_current_last_command = None

# set되어 있으면 "순찰 중". patrol_stop이나 수동 명령, 장애물 감지 시 clear된다.
_patrol_active = threading.Event()


def _set_state(state: str, last_command: str = None) -> None:
    """현재 상태를 갱신하고 즉시 store(=Supabase 또는 로컬 JSON)에도 반영한다."""
    global _current_state, _current_last_command
    with _state_lock:
        _current_state = state
        _current_last_command = last_command
    store.update_status(state=state, last_command=last_command)


def _heartbeat_loop() -> None:
    """
    메인 폴링 루프와 완전히 별개로 계속 도는 백그라운드 스레드.
    명령을 처리하느라 바쁠 때도(예: _move의 sleep 중) heartbeat가
    끊기면 안 되기 때문에 스레드로 분리했다.
    """
    while True:
        time.sleep(HEARTBEAT_INTERVAL_SEC)
        with _state_lock:
            state, last_command = _current_state, _current_last_command
        try:
            store.update_status(state=state, last_command=last_command)
            print(f"[MOCK ROBOT] (heartbeat) state={state}")
        except Exception as exc:
            # heartbeat 스레드가 죽으면 웹이 계속 OFFLINE으로 보게 되므로
            # 여기서 죽지 않고 다음 주기에 다시 시도한다.
            print(f"[MOCK ROBOT] (heartbeat) 갱신 실패: {exc}")


def _measure_distance_cm():
    """
    초음파 센서(HC-SR04류)로 거리를 재서 cm로 반환한다. GPIO 없으면(노트북 등)
    또는 측정 실패(타임아웃) 시 None을 반환한다. Yahboom 튜토리얼 예제와
    동일한 방식(Trig 10us 펄스 → Echo 하이 유지시간으로 거리 계산).
    """
    if GPIO is None:
        return None

    GPIO.output(TRIG_PIN, GPIO.LOW)
    time.sleep(0.000002)
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.000015)
    GPIO.output(TRIG_PIN, GPIO.LOW)

    t3 = time.time()
    while not GPIO.input(ECHO_PIN):
        if time.time() - t3 > 0.03:
            return None
    t1 = time.time()
    while GPIO.input(ECHO_PIN):
        if time.time() - t1 > 0.03:
            return None
    t2 = time.time()
    return (t2 - t1) * 340 / 2 * 100


def _check_obstacle() -> bool:
    """
    초음파 센서로 전방 장애물을 감지한다.
    GPIO가 없으면(노트북 등) 항상 False(mock). 실물에서는 거리를 재서
    OBSTACLE_STOP_DISTANCE_CM 이하면 True.
    """
    distance = _measure_distance_cm()
    if distance is None:
        return False
    return distance <= OBSTACLE_STOP_DISTANCE_CM


def _move(command: str) -> None:
    """
    전진/후진/좌회전/우회전/정지를 실행한다.

    _car가 있으면(실물 로봇, YB_Pcb_Car 로드 성공) 실제 모터를 돌리고,
    없으면(노트북 등) 로그만 찍고 sleep으로 흉내낸다 — 코드 하나로 두
    환경 다 돌아가게 만들어서, 팀원이 노트북에서 이 코드를 테스트할 때도
    안 깨지게 했다.

    left/right는 반드시 "제자리 회전"이어야 한다 (전진하며 도는 것 아님) —
    그래서 Car_Left/Car_Right(곡선주행)가 아니라 Car_Spin_Left/Car_Spin_Right
    (제자리 회전)를 쓴다. 실물에서 직접 확인 완료(2026.08.26).
    """
    label = {
        "forward": "전진",
        "backward": "후진",
        "left": "제자리 좌회전",
        "right": "제자리 우회전",
        "stop": "정지",
    }.get(command, command)

    print(f"[ROBOT] 모터 동작: {label}")
    _set_state("moving", command)

    # 제자리 회전은 전진/후진보다 훨씬 짧게 돌아야 조금씩만 돈다.
    duration = SPIN_DURATION_SEC if command in ("left", "right") else MOVE_DURATION_SEC

    if _car is not None:
        if command == "forward":
            _car.Car_Run(MOVE_SPEED, MOVE_SPEED)
        elif command == "backward":
            _car.Car_Back(MOVE_SPEED, MOVE_SPEED)
        elif command == "left":
            _car.Car_Spin_Left(MOVE_SPEED, MOVE_SPEED)
        elif command == "right":
            _car.Car_Spin_Right(MOVE_SPEED, MOVE_SPEED)
        elif command == "stop":
            _car.Car_Stop()

        if command != "stop":
            time.sleep(duration)  # 이만큼 움직이고
            _car.Car_Stop()  # 자동으로 정지 (계속 움직이면 안 되니까)
    else:
        if command != "stop":
            time.sleep(duration)  # mock: 흉내만

    print(f"[ROBOT] {label} 완료")
    _set_state("stopped" if command == "stop" else "idle", command)


STREAM_SNAPSHOT_URL = f"http://localhost:{os.environ.get('STREAM_PORT', '8090')}/snapshot.jpg"


def _grab_frame_from_stream_server():
    """
    stream_server.py(MJPEG 실시간 스트리밍 서버)가 떠있으면, 거기서 이미
    찍고 있는 최신 프레임을 그대로 받아온다.

    rpicam-vid(스트리밍)와 rpicam-still(직접 촬영)이 카메라를 동시에 열면
    충돌할 수 있어서(실물 카메라는 한 번에 한 프로세스만 붙을 수 있음),
    "실시간 화면 보면서 캡처도 하고 싶다"는 요청에 맞춰 추가함
    (2026.08.27) — 스트리밍 서버가 안 떠있으면 그냥 실패하고 아래
    _grab_frame_rpicam()으로 자연스럽게 넘어간다.
    """
    import urllib.request

    try:
        with urllib.request.urlopen(STREAM_SNAPSHOT_URL, timeout=2) as resp:
            data = resp.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is not None:
            print("[ROBOT] 스트리밍 서버에서 프레임 재사용 (카메라 재오픈 없음)")
        return frame
    except Exception:
        return None  # 스트리밍 서버가 안 떠있거나 응답 없음 — 조용히 다음 방법으로


def _grab_frame_rpicam():
    """
    Razbot 실물 카메라(CSI 카메라, libcamera 스택)로 촬영한다.

    이 카메라는 rp1-cfe/pispbe 드라이버를 쓰는 CSI 카메라라서 일반 USB
    웹캠처럼 cv2.VideoCapture()로 바로 프레임을 못 읽는다(장치는 열리지만
    read()가 계속 실패함 — 실물 테스트로 확인, 2026.08.26). picamera2
    파이썬 라이브러리는 시스템에 깔려있지만 numpy 바이너리 호환성이 깨져
    있어서(pip로 새 numpy가 깔리면서 충돌) 대신 rpicam-still 커맨드라인
    도구를 서브프로세스로 호출해서 JPEG 바이트를 표준출력으로 받는다.

    카메라가 실제로 거꾸로 장착돼 있어서(실물 테스트로 확인, 2026.08.26)
    --rotation 180 없이 찍으면 위아래가 뒤집힌 사진이 나온다. 이게 YOLO
    오탐지(물병을 backpack으로 잘못 판단)의 원인 중 하나로 의심돼서 추가함.

    기본 화이트밸런스(auto)로 찍으면 사진 전체가 초록/청록빛으로 심하게
    틀어져 나오는 것도 실물 테스트로 발견함 — --awb daylight로 바꾸니
    훨씬 자연스러운 색으로 나옴 (2026.08.26).
    """
    try:
        result = subprocess.run(
            [RPICAM_STILL, "-o", "-", "-t", "1000", "-n", "--rotation", "180",
             "--awb", "daylight", "--width", "1296", "--height", "972"],
            capture_output=True, timeout=15, check=True,
        )
        arr = np.frombuffer(result.stdout, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            print("[ROBOT] rpicam-still 출력 디코딩 실패")
        return frame
    except Exception as exc:
        print(f"[ROBOT] rpicam-still 촬영 실패: {exc}")
        return None


def _grab_frame_webcam():
    """웹캠(cv2.VideoCapture)으로 촬영한다 — 노트북 등 CSI 카메라가 없는 환경용."""
    cam = cv2.VideoCapture(WEBCAM_INDEX)
    if not cam.isOpened():
        print(f"[MOCK ROBOT] 웹캠(index={WEBCAM_INDEX})을 열 수 없습니다")
        cam.release()
        return None

    # 웹캠은 켜자마자 첫 프레임이 어둡거나 초점이 안 맞는 경우가 많아서
    # 몇 프레임 미리 읽어 버리고(워밍업) 그 다음 프레임을 실제로 사용한다.
    frame = None
    for _ in range(5):
        ok, frame = cam.read()
        if not ok:
            frame = None
            break
    cam.release()
    return frame


def _grab_frame():
    """
    "카메라에서 이미지 한 장을 가져오는" 부분만 따로 뺀 함수.

    rpicam-still이 있으면(실물 Razbot, CSI 카메라) 그걸로 촬영하고,
    없으면(노트북 등) 웹캠으로 촬영한다 — 자동 분기라 코드 하나로 두
    환경 다 돌아간다. "이미지를 저장/전달하는 방식"(_capture)과 분리해둔
    덕분에 이 함수 안쪽만 통째로 교체해서 실물로 전환할 수 있었다.

    반환값: cv2 이미지(numpy 배열) 또는 실패 시 None.
    """
    if cv2 is None:
        print("[MOCK ROBOT] opencv-python이 설치되어 있지 않습니다 (pip install opencv-python)")
        return None

    if RPICAM_STILL:
        frame = _grab_frame_from_stream_server()
        if frame is not None:
            return frame
        return _grab_frame_rpicam()
    return _grab_frame_webcam()


def _capture() -> None:
    """
    촬영을 처리한다.
    _grab_frame()으로 이미지를 가져와서 data/captures/ 에 jpg로 저장한다.
    가져오기 실패 시(카메라 없음 등)에는 placeholder 파일을 남긴다.
    """
    os.makedirs(CAPTURES_DIR, exist_ok=True)
    frame = _grab_frame()

    if frame is not None:
        filename = f"capture_{int(time.time())}.jpg"
        path = os.path.join(CAPTURES_DIR, filename)
        # 주의: cv2.imwrite(path, frame)는 경로에 한글 등 non-ASCII 문자가
        # 있으면 Windows에서 에러 없이 조용히 실패한다(False만 반환).
        # 이 프로젝트 폴더 경로 자체에 한글이 포함돼 있어서, imencode로
        # 메모리에 인코딩한 뒤 파이썬 파일 IO로 직접 쓰는 방식을 쓴다.
        ok, buf = cv2.imencode(".jpg", frame)
        if ok:
            with open(path, "wb") as f:
                f.write(buf.tobytes())
            print(f"[MOCK ROBOT] 촬영 완료 (저장: {path})")
        else:
            print("[MOCK ROBOT] 이미지 인코딩 실패")
            frame = None  # 아래 placeholder 분기로 떨어지게

    if frame is None:
        filename = f"capture_{int(time.time())}.txt"
        path = os.path.join(CAPTURES_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("이 파일은 실제 사진 대신 만든 자리표시자(placeholder)입니다.\n")
            f.write("웹캠을 못 가져와서(카메라 없음/opencv 미설치) 대체로 남깁니다.\n")
        print(f"[MOCK ROBOT] 촬영 실패 → placeholder 저장: {path}")


def _buzz() -> None:
    """
    부저 울림을 흉내낸다.

    주의: "buzz"는 팀 Supabase 계약(robot_commands.command 8종)에
    없는 값이다. RLS 정책이 8종 외의 command는 INSERT 자체를 막기
    때문에, 실제 웹/Supabase를 통해서는 이 함수가 절대 호출되지 않는다.
    지금은 send_command.py로 로컬 JSON 모드에서만 테스트 가능 — 부저를
    실제로 언제 울릴지(예: patrol_start 시 자동으로)는 팀과 상의 필요.
    """
    print("[MOCK ROBOT] 부저 울림 (삑삑)")
    if winsound is not None:
        for _ in range(2):
            winsound.Beep(1000, 150)  # 1000Hz, 150ms
            time.sleep(0.1)
    else:
        print("[MOCK ROBOT] (이 환경에서는 실제 소리 재생 불가 — winsound 없음)")


def _read_tracking():
    """
    4채널 라인트레이싱 센서 값을 읽는다. (Left1, Left2, Right1, Right2)
    각 값은 0(검은선 감지) 또는 1(흰 바탕). GPIO 없으면(노트북 등) None.
    """
    if GPIO is None:
        return None
    return (
        GPIO.input(TRACKING_LEFT1),
        GPIO.input(TRACKING_LEFT2),
        GPIO.input(TRACKING_RIGHT1),
        GPIO.input(TRACKING_RIGHT2),
    )


def _patrol_steer(l1: int, l2: int, r1: int, r2: int) -> None:
    """
    센서 값을 보고 아주 짧게 방향을 조정한다. 간단한 규칙 기반:
    - 안쪽 두 센서(L2, R1)가 둘 다 검은선 위 → 직진
    - 왼쪽으로 라인이 치우침(L1/L2가 검은선) → 좌회전으로 보정
    - 오른쪽으로 치우침(R1/R2가 검은선) → 우회전으로 보정
    - 전부 흰색(라인을 완전히 놓침) → 일단 정지
    실물 캘리브레이션 전 초기 버전이라, 나중에 실제 순찰맵으로 테스트하며
    조정이 더 필요할 수 있다.
    """
    if _car is None:
        return
    if l2 == 0 and r1 == 0:
        _car.Car_Run(PATROL_SPEED, PATROL_SPEED)
    elif l1 == 0 or l2 == 0:
        _car.Car_Spin_Left(PATROL_SPEED, PATROL_SPEED)
    elif r1 == 0 or r2 == 0:
        _car.Car_Spin_Right(PATROL_SPEED, PATROL_SPEED)
    else:
        _car.Car_Stop()


def _patrol_scripted_demo() -> None:
    """
    시연 영상용 고정 시퀀스: 앞으로 70cm → 우회전(약 90도) → 앞으로 30cm.
    실제 라인 센서를 안 보고 그냥 시간 기반으로 움직인다 — PATROL_DEMO_MODE가
    True일 때만 _patrol_loop() 대신 이게 호출된다.
    """
    print("[MOCK ROBOT] 순찰(시연 시퀀스) 시작: 전진70cm→우회전→전진30cm")
    _set_state("moving", "patrol_start")
    try:
        if _car is not None:
            _car.Car_Run(PATROL_SPEED, PATROL_SPEED)
            time.sleep(DEMO_FORWARD1_SEC)
            _car.Car_Stop()

            _car.Car_Spin_Right(PATROL_SPEED, PATROL_SPEED)
            time.sleep(DEMO_TURN_SEC)
            _car.Car_Stop()

            _car.Car_Run(PATROL_SPEED, PATROL_SPEED)
            time.sleep(DEMO_FORWARD2_SEC)
            _car.Car_Stop()
        else:
            time.sleep(DEMO_FORWARD1_SEC + DEMO_TURN_SEC + DEMO_FORWARD2_SEC)  # mock: 흉내만
        print("[MOCK ROBOT] 순찰(시연 시퀀스) 종료")
    finally:
        _patrol_active.clear()
        _set_state("idle", "patrol_stop")


def _patrol_loop() -> None:
    """
    라인트레이싱 기반 자동순찰 루프 (SLAM 아님 — 바닥에 그려진 정해진
    라인을 따라가는 방식).

    patrol_start로 시작되고, 아래 중 하나라도 발생하면 즉시 종료된다:
    - patrol_stop 명령 (_patrol_active.clear() 로 정상 종료)
    - 수동 명령(forward/backward/left/right/stop) — 안전 정지가 항상 우선
    - 장애물 감지(_check_obstacle)
    """
    if PATROL_DEMO_MODE:
        _patrol_scripted_demo()
        return
    # 이 함수는 별도 스레드에서 돈다 — _handle_command의 try/except는
    # "스레드를 시작시키는 순간"만 감싸지, 스레드 안에서 나중에 터지는
    # 예외는 못 잡는다(파이썬 스레드 예외는 부모로 전파되지 않음). 그래서
    # 이 함수 전체를 자체적으로 try/except로 감싸 "에러시 정지 우선"
    # 원칙을 여기서도 지킨다.
    try:
        print("[MOCK ROBOT] 순찰 시작 (라인트레이싱)")
        _set_state("moving", "patrol_start")

        while _patrol_active.is_set():
            if _check_obstacle():
                print(f"[MOCK ROBOT] 전방 {OBSTACLE_STOP_DISTANCE_CM}cm 이내 장애물 감지 → 안전 정지")
                if _car is not None:
                    _car.Car_Stop()
                _patrol_active.clear()
                _set_state("stopped", "patrol_stop(obstacle)")
                return

            tracking = _read_tracking()
            if tracking is not None:
                _patrol_steer(*tracking)
                time.sleep(0.1)  # 라인 이탈에 빠르게 반응하려고 짧게
            else:
                time.sleep(0.5)  # mock: 센서 없어서 그냥 순찰 중이라는 것만 흉내

        print("[MOCK ROBOT] 순찰 종료")
        if _car is not None:
            _car.Car_Stop()
        _set_state("idle", "patrol_stop")
    except Exception as exc:
        print(f"[MOCK ROBOT] 순찰 중 오류 발생 → 안전 정지: {exc}")
        if _car is not None:
            try:
                _car.Car_Stop()
            except Exception:
                pass
        _patrol_active.clear()


def _start_patrol() -> None:
    if _patrol_active.is_set():
        print("[MOCK ROBOT] 이미 순찰 중입니다")
        return
    _patrol_active.set()
    threading.Thread(target=_patrol_loop, daemon=True).start()


def _stop_patrol() -> None:
    _patrol_active.clear()


def _handle_command(record: dict) -> None:
    command = record["command"]
    try:
        if command in ("forward", "backward", "left", "right", "stop"):
            if _patrol_active.is_set():
                print("[MOCK ROBOT] 수동 명령이 순찰보다 우선 — 순찰 중단")
                _stop_patrol()
            _move(command)
        elif command == "capture":
            _capture()
        elif command == "buzz":
            _buzz()
        elif command == "patrol_start":
            _start_patrol()
        elif command == "patrol_stop":
            _stop_patrol()
        else:
            print(f"[MOCK ROBOT] 알 수 없는 명령: {command}")
    except Exception as exc:
        # 팀 계약: 어떤 예외든 로봇을 먼저 정지시키고 나서 로그를 남긴다.
        print(f"[MOCK ROBOT] 처리 중 오류 발생 → 안전 정지: {exc}")
        _stop_patrol()
        try:
            _move("stop")
        except Exception:
            pass

    try:
        store.mark_command_done(record["id"])
    except Exception as exc:
        # 이 호출이 실패해도(예: 권한 문제) 프로그램 전체가 죽으면 안 된다 —
        # 다음 polling 주기에 같은 명령을 다시 집어서 중복 처리할 위험은
        # 있지만, 최소한 로봇 자체는 계속 명령을 받을 수 있는 상태를 유지한다.
        print(f"[MOCK ROBOT] 명령 완료 처리 실패: {exc}")


def run():
    store.init_store()
    threading.Thread(target=_heartbeat_loop, daemon=True).start()
    print("[MOCK ROBOT] 대기 중... (Ctrl+C로 종료)")
    if store.USE_SUPABASE:
        print(f"[MOCK ROBOT] robot_commands 테이블 polling 중 ({store.SUPABASE_URL})")
    else:
        print(f"[MOCK ROBOT] 명령 파일 위치: {store.COMMANDS_FILE}")

    while True:
        try:
            pending = store.get_pending_commands()
        except Exception as exc:
            # 네트워크 순간 끊김/Supabase 일시 장애 등으로 폴링 자체가
            # 실패해도 프로그램 전체가 죽으면 안 된다 — 로그만 남기고
            # 다음 주기에 다시 시도한다. (heartbeat, mark_command_done과
            # 같은 "죽지 않고 계속 시도" 원칙을 폴링 루프에도 적용)
            print(f"[MOCK ROBOT] 명령 조회 실패(다음 주기에 재시도): {exc}")
            pending = []

        for record in pending:
            print(f"\n[MOCK ROBOT] 새 명령 수신: id={record['id']} command={record['command']}")
            _handle_command(record)
        time.sleep(1)  # 1초마다 새 명령이 있는지 확인 (polling)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n[ROBOT] 종료합니다.")
    finally:
        if _car is not None:
            # Yahboom 문서 권장사항: 안 지워두면 다음 실행 때 I2C 장치가
            # "이미 점유중"이라는 에러가 날 수 있다.
            del _car
