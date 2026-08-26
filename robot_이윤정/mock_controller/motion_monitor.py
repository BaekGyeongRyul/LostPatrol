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
프로세스라 라즈베리파이에서 이 스크립트만 따로 실행하면 된다. 카메라
자체는 controller.py의 capture 명령과 별개로 이 스크립트가 직접 촬영한다
(같은 카메라 장치를 물리적으로 동시에 두 프로세스가 열면 충돌할 수 있으니,
capture 명령을 자주 쓰는 상황이라면 주의).

동작 방식:
    1. MOTION_INTERVAL_SEC마다 실물 카메라(rpicam-still)로 한 장 촬영
       (controller.py의 _grab_frame_rpicam()과 동일한 촬영 설정 — 실물
       테스트로 확정된 rotation 180 / awb daylight 그대로 맞춤)
    2. Haar cascade(정면 얼굴)로 얼굴 검출 → person_detected
    3. 이전 프레임과 흑백 픽셀 차이(absdiff)를 비교해서 변한 픽셀 비율로
       motion_severity(normal/warning/danger) 판단 — 임계값은 TBD,
       실물로 몇 번 테스트해보면서 조정 필요
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

MOTION_INTERVAL_SEC = 3  # 이 주기로 촬영/판단해서 Supabase에 반영

# Yahboom Raspbot에 이미 있는 Haar cascade 모델 파일. 없는 환경(노트북 등)
# 에서는 얼굴 검출 없이 움직임 판단만 동작한다.
FACE_CASCADE_PATH = os.environ.get(
    "FACE_CASCADE_PATH",
    os.path.expanduser("~/Yahboom_project/Raspbot/raspbot/haarcascade_frontalface_default.xml"),
)

DEFAULT_LOCATION = os.environ.get("DEFAULT_LOCATION", "A구역")

# TBD - 팀 협의 후 확정. 실물 테스트로 몇 번 돌려보면서 맞는 값 찾아야 함.
# 변한 픽셀 비율(%) 기준. 처음엔 1.0/5.0으로 뒀다가 실물 테스트에서 아무도
# 없어도 계속 danger로 뜨는 문제 발견(2026.08.27) — rpicam-still을 매번
# 새 프로세스로 찍다 보니 사진마다 자동노출/화이트밸런스가 미묘하게 달라져서
# 실제 움직임 없이도 픽셀 차이가 크게 잡히는 게 원인으로 추정. 임계값을
# 훨씬 높이고, 비교 전에 블러 처리를 추가해서 이런 미세한 노이즈에 덜
# 민감하게 만듦.
MOTION_WARNING_PCT = 10.0
MOTION_DANGER_PCT = 25.0

_face_cascade = None
if cv2 is not None and os.path.exists(FACE_CASCADE_PATH):
    _face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
    print(f"[MOTION] 얼굴 검출 모델 로드 완료: {FACE_CASCADE_PATH}")
else:
    print(f"[MOTION] 얼굴 검출 모델 없음({FACE_CASCADE_PATH}) — person_detected는 항상 False로 동작")

_prev_gray = None  # 직전 프레임(흑백) — 움직임 비교용
_last_person_detected = False  # 상태가 "바뀐 순간"에만 patrol_events 기록하려고 기억


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
    if RPICAM_STILL:
        return _grab_frame_rpicam()
    return _grab_frame_webcam()


def _detect_person(gray) -> bool:
    if _face_cascade is None:
        return False
    faces = _face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return len(faces) > 0


def _motion_severity(prev_gray, gray) -> str:
    """이전 프레임과 비교해서 변한 픽셀 비율(%)로 움직임 정도를 판단한다."""
    if prev_gray is None:
        return "normal"  # 첫 프레임은 비교 대상이 없음

    # 매번 rpicam-still을 새 프로세스로 찍다 보니 자동노출/화이트밸런스가
    # 사진마다 미세하게 달라져서 생기는 노이즈를 줄이려고 블러 처리 후 비교.
    prev_blur = cv2.GaussianBlur(prev_gray, (21, 21), 0)
    cur_blur = cv2.GaussianBlur(gray, (21, 21), 0)

    diff = cv2.absdiff(prev_blur, cur_blur)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    changed_pct = (cv2.countNonZero(thresh) / thresh.size) * 100

    if changed_pct >= MOTION_DANGER_PCT:
        return "danger"
    if changed_pct >= MOTION_WARNING_PCT:
        return "warning"
    return "normal"


def _handle_frame(frame) -> None:
    global _prev_gray, _last_person_detected

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    person_detected = _detect_person(gray)
    motion_severity = _motion_severity(_prev_gray, gray)
    _prev_gray = gray

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
