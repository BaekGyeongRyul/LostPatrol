"""
motion_monitor.py — 카메라로 사람/움직임을 감지해서 Supabase safety_status의
motion_severity / person_detected를 채우는 독립 프로그램.

원래 이 두 컬럼은 조은수(Vision) 담당으로 설계돼있었는데
(robot_이윤정/HARDWARE_REFERENCE.md 참고), 아직 구현 전이라 이윤정이 직접
작성함(2026.08.27) — Yahboom Raspbot 예제(`3.AI Vision course/08.Face
detection`)가 쓰는 것과 같은 방식(OpenCV Haar cascade)을 그대로 활용했고,
필요한 모델 파일도 이미 `~/Yahboom_project/Raspbot/raspbot/`에 있는 걸
그대로 씀.

controller.py(모터)나 safety_monitor.py(아두이노)와는 완전히 독립된
프로세스라 라즈베리파이에서 이 스크립트만 따로 실행하면 된다. 카메라는
stream_server.py가 떠있으면 거기서 찍고 있는 최신 프레임을 재사용하고
(2026.08.29 추가 — 카메라 충돌 방지, controller.py와 동일한 패턴),
stream_server.py가 없으면 이 스크립트가 직접 rpicam-still로 촬영한다.

동작 방식:
    1. MOTION_INTERVAL_SEC마다 프레임 한 장 확보 — stream_server.py 재사용
       우선, 없으면 실물 카메라(rpicam-still) 직접 촬영(controller.py의
       _grab_frame_rpicam()과 동일한 촬영 설정 — 실물 테스트로 확정된
       rotation 180 / awb daylight 그대로 맞춤)
    2. Haar cascade(정면 얼굴)로 얼굴 검출 → person_detected
    3. motion_severity는 person_detected를 그대로 반영(감지되면 danger,
       아니면 normal) — 원래는 픽셀 diff 기반으로 따로 판단했는데, 웹에서
       "PERSON DETECTED/NO MOTION" 문구(person_detected 기준)와 빨간/초록
       색상(motion_severity 기준)이 서로 안 맞게 보이는 문제가 있었고,
       stream_server 프레임 재사용으로 바꾸면서 영상 압축 노이즈 때문에
       diff 기반 판단이 더 불안정해져서 2026.08.29에 단순화함.
    4. store.update_safety_status(motion_severity=..., person_detected=...)
       — 이 함수는 넘긴 필드만 갱신하고 나머지(화재/소음 등)는 안 건드림
       (store.py 참고)

노트북(Windows) 등 rpicam-still이 없는 환경에서는 웹캠으로 자동 대체된다
(controller.py의 _grab_frame_webcam()과 동일한 패턴).
"""

import os
import shutil
import subprocess
import time

import store

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

RPICAM_STILL = shutil.which("rpicam-still")
WEBCAM_INDEX = 0
STREAM_SNAPSHOT_URL = f"http://localhost:{os.environ.get('STREAM_PORT', '8090')}/snapshot.jpg"

MOTION_INTERVAL_SEC = 3  # 이 주기로 촬영/판단해서 Supabase에 반영

# Yahboom Raspbot에 이미 있는 Haar cascade 모델 파일. 없는 환경(노트북 등)
# 에서는 얼굴 검출 없이 움직임 판단만 동작한다.
FACE_CASCADE_PATH = os.environ.get(
    "FACE_CASCADE_PATH",
    os.path.expanduser("~/Yahboom_project/Raspbot/raspbot/haarcascade_frontalface_default.xml"),
)

DEFAULT_LOCATION = os.environ.get("DEFAULT_LOCATION", "A구역")

_face_cascade = None
if cv2 is not None and os.path.exists(FACE_CASCADE_PATH):
    _face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
    print(f"[MOTION] 얼굴 검출 모델 로드 완료: {FACE_CASCADE_PATH}")
else:
    print(f"[MOTION] 얼굴 검출 모델 없음({FACE_CASCADE_PATH}) — person_detected는 항상 False로 동작")

_last_person_detected = False  # 상태가 "바뀐 순간"에만 patrol_events 기록하려고 기억
_ever_detected = False  # 한 번 감지되면 계속 True로 유지(래치) — 재시작해야 초기화됨


def _grab_frame_from_stream_server():
    """
    controller.py의 _grab_frame_from_stream_server()와 동일한 목적.
    stream_server.py(rpicam-vid)가 이미 카메라를 붙잡고 있는 상태에서
    motion_monitor.py가 별도로 rpicam-still을 또 열면 카메라 충돌이 나서
    촬영 실패(exit 255)하거나 스트리밍 화면 자체가 잠깐 깨지는(색/방향
    이상해짐) 문제가 있었다(2026.08.29) — stream_server.py가 떠있으면
    거기서 이미 찍고 있는 최신 프레임을 그대로 재사용해서 카메라를 다시
    열지 않도록 함. stream_server.py가 안 떠있으면 조용히 실패하고
    아래 _grab_frame_rpicam()으로 자연스럽게 넘어간다.
    """
    import urllib.request

    try:
        with urllib.request.urlopen(STREAM_SNAPSHOT_URL, timeout=2) as resp:
            data = resp.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def _grab_frame_rpicam():
    """controller.py의 _grab_frame_rpicam()과 동일한 촬영 설정."""
    try:
        result = subprocess.run(
            [RPICAM_STILL, "-o", "-", "-t", "1000", "-n", "--rotation", "180",
             "--awb", "daylight", "--width", "1296", "--height", "972"],
            capture_output=True, timeout=15, check=True,
        )
        arr = np.frombuffer(result.stdout, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception as exc:
        print(f"[MOTION] rpicam-still 촬영 실패: {exc}")
        return None


def _grab_frame_webcam():
    cam = cv2.VideoCapture(WEBCAM_INDEX)
    if not cam.isOpened():
        cam.release()
        return None
    frame = None
    for _ in range(5):
        ok, frame = cam.read()
        if not ok:
            frame = None
            break
    cam.release()
    return frame


def _grab_frame():
    if cv2 is None:
        return None
    frame = _grab_frame_from_stream_server()
    if frame is not None:
        return frame
    if RPICAM_STILL:
        return _grab_frame_rpicam()
    return _grab_frame_webcam()


def _detect_person(gray) -> bool:
    if _face_cascade is None:
        return False
    faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return len(faces) > 0


def _handle_frame(frame) -> None:
    global _last_person_detected, _ever_detected

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    person_detected = _detect_person(gray)

    # 한 번이라도 감지되면 이후 프레임에서 얼굴이 안 잡혀도(각도/거리 때문에
    # 놓치는 경우가 잦음) 계속 감지된 상태로 유지해달라는 요청(2026.08.29).
    # 다시 False로 돌아가게 하려면 motion_monitor.py를 재시작하면 된다.
    if person_detected:
        _ever_detected = True
    person_detected = _ever_detected

    # 원래는 픽셀 변화율(_motion_severity)로 danger/warning/normal을 따로
    # 판단했는데, 웹(LivePatrol.jsx)에서 "PERSON DETECTED/NO MOTION" 문구는
    # person_detected 기준, 빨간색/초록색 표시는 motion_severity 기준으로
    # 서로 다른 값을 봐서 둘이 안 맞게(글자랑 색이 따로 노는) 보이는 문제가
    # 있었다(2026.08.29). 게다가 stream_server 프레임 재사용으로 바꾸면서
    # (영상 압축 노이즈 때문에) 픽셀 변화율 판단이 더 불안정해짐. "사람
    # 감지되면 빨강, 아니면 초록"이 실제 요구사항이라 motion_severity를
    # person_detected 기준으로 단순화함.
    motion_severity = "danger" if person_detected else "normal"

    store.update_safety_status(
        motion_severity=motion_severity,
        person_detected=person_detected,
    )
    print(f"[MOTION] person_detected={person_detected} motion_severity={motion_severity}")

    # 상태가 "바뀐 순간"에만 이벤트를 기록한다 (safety_monitor.py와 같은 원칙)
    # event_type은 docs/HARDWARE_REFERENCE.md에 예시로 나온 "motion_detected" 그대로 사용.
    if person_detected and not _last_person_detected:
        store.add_patrol_event("motion_detected", DEFAULT_LOCATION, "사람 감지됨", "normal")
    _last_person_detected = person_detected


def run():
    store.init_store()
    mode = "실물(rpicam-still)" if RPICAM_STILL else "mock(웹캠)"
    print(f"[MOTION] 움직임/사람 감지 모니터 시작 — {mode} 모드, {MOTION_INTERVAL_SEC}초 주기")

    while True:
        try:
            frame = _grab_frame()
            if frame is not None:
                _handle_frame(frame)
            else:
                print("[MOTION] 촬영 실패 — 다음 주기에 재시도")
        except Exception as exc:
            # 다른 프로그램들과 동일한 원칙: 죽지 않고 로그 남기고 계속 시도
            print(f"[MOTION] 처리 중 오류(다음 주기에 재시도): {exc}")
        time.sleep(MOTION_INTERVAL_SEC)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n[MOTION] 종료합니다.")
