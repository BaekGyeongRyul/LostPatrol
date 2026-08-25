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
import threading
import store

try:
    import winsound  # Windows 전용. 노트북에서 실제 "삑" 소리를 내기 위함.
except ImportError:
    winsound = None

try:
    import cv2
except ImportError:
    cv2 = None

WEBCAM_INDEX = 0  # 노트북 기본 웹캠. 카메라가 여러 개면 1, 2...로 바꿔서 테스트

# 이동 명령이 실제로 걸리는 시간(초)을 흉내내기 위한 값.
# 진짜 로봇에서는 "모터가 도는 시간"이 되고, 지금은 그냥 sleep이다.
MOVE_DURATION_SEC = 1.5

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


def _check_obstacle() -> bool:
    """
    초음파 센서로 전방 장애물을 감지한다.
    지금은 센서가 없어서 항상 False. 실물 연동 시: 거리(cm)를 읽어서
    OBSTACLE_STOP_DISTANCE_CM 이하면 True를 반환하도록 교체한다.
    """
    return False


def _move(command: str) -> None:
    """
    전진/후진/좌회전/우회전/정지를 흉내낸다.
    실제 하드웨어가 오면 여기서 Yahboom 모터 제어 함수를 호출하게 된다.
    예) robot.forward(speed) / robot.turn_left(speed) 등
    left/right는 반드시 "제자리 회전"이어야 한다 (전진하며 도는 것 아님).
    """
    label = {
        "forward": "전진",
        "backward": "후진",
        "left": "제자리 좌회전",
        "right": "제자리 우회전",
        "stop": "정지",
    }.get(command, command)

    print(f"[MOCK ROBOT] 모터 동작: {label}")
    _set_state("moving", command)

    if command != "stop":
        time.sleep(MOVE_DURATION_SEC)  # 실제로는 모터가 도는 시간

    print(f"[MOCK ROBOT] {label} 완료")
    _set_state("stopped" if command == "stop" else "idle", command)


def _grab_frame():
    """
    "카메라에서 이미지 한 장을 가져오는" 부분만 따로 뺀 함수.

    지금은 노트북 웹캠(cv2.VideoCapture)으로 가져오지만, 실제 로봇이
    오면 이 안쪽 구현이 완전히 바뀔 수 있다 — Yahboom 카메라는 웹캠처럼
    단순 device index가 아니라 라즈베리파이가 띄운 WebSocket 영상
    스트림(포트 6001)에서 프레임을 받아오는 방식일 가능성이 있기 때문.
    그래서 "이미지를 저장/전달하는 방식"(_capture)과 "이미지를 어디서
    가져오는지"(_grab_frame)를 분리해뒀다 — 나중엔 이 함수 안쪽만
    통째로 교체하면 된다.

    반환값: cv2 이미지(numpy 배열) 또는 실패 시 None.
    """
    if cv2 is None:
        print("[MOCK ROBOT] opencv-python이 설치되어 있지 않습니다 (pip install opencv-python)")
        return None

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


def _patrol_loop() -> None:
    """
    라인트레이싱 기반 자동순찰 루프 (SLAM 아님 — 바닥에 그려진 정해진
    라인을 따라가는 방식). 지금은 실제 라인트레이싱 센서가 없어서 mock.

    patrol_start로 시작되고, 아래 중 하나라도 발생하면 즉시 종료된다:
    - patrol_stop 명령 (_patrol_active.clear() 로 정상 종료)
    - 수동 명령(forward/backward/left/right/stop) — 안전 정지가 항상 우선
    - 장애물 감지(_check_obstacle)
    """
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
                _patrol_active.clear()
                _set_state("stopped", "patrol_stop(obstacle)")
                return
            # 실물 연동 시: 4채널 라인트레이싱 센서 값 읽어서 조향 보정.
            # 지금은 순찰 중이라는 것만 흉내낸다.
            time.sleep(0.5)

        print("[MOCK ROBOT] 순찰 종료")
        _set_state("idle", "patrol_stop")
    except Exception as exc:
        print(f"[MOCK ROBOT] 순찰 중 오류 발생 → 안전 정지: {exc}")
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
        print("\n[MOCK ROBOT] 종료합니다.")
