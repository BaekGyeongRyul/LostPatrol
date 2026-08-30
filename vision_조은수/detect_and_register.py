"""
detect_and_register.py — 촬영된 이미지를 YOLO로 분석해서 분실물로 판단되면
Supabase(Storage + lost_items)에 자동 등록한다.

담당: 조은수(Vision/YOLO). 원래 이 저장소(vision_조은수/)에 있어야 할
"모델 → Supabase 연결" 부분이 비어있어서, 이윤정이 초안을 만들어뒀습니다
(2026.08.26). 모델 학습(best.pt, LOSTITEM-1 데이터셋)은 조은수가 완료한
것을 https://github.com/eunsoo0229/LostPatrolAI 에서 그대로 가져왔습니다.
수정/개선 자유롭게 하세요 — 이건 팀이 오늘 안에 엔드투엔드로 확인해보기
위한 시작점입니다.

## 이게 하는 일

1. 이미지 폴더(기본: robot_이윤정/mock_controller/data/captures/)를 주기적으로
   감시해서 새로 생긴 사진을 찾는다. (로봇의 capture 명령이 저장하는 바로 그
   폴더 — 로봇 프로세스랑은 완전히 독립적으로, 파일 시스템만 공유한다)
2. 각 새 사진에 대해 YOLO(best.pt)로 물체를 감지한다.
3. 감지된 물체 중 신뢰도가 CONFIDENCE_THRESHOLD 이상이고, 우리가 다루는
   3종(backpack/wallet/waterbottle→bottle) 중 하나면 "분실물 후보"로
   본다.
4. 같은 클래스가 CONSECUTIVE_REQUIRED번 연속 감지되면(오탐 방지), 그 사진을
   Supabase Storage(lost-item-photos)에 업로드하고 lost_items에 새 행을
   등록한다 (status='new').

## 클래스 이름 매핑 (중요)

조은수 모델은 `waterbottle`이라는 이름을 쓰는데, 팀 Data Contract
(docs/02_SUPABASE_DATA_CONTRACT.md)는 `bottle`로 고정돼 있다. 이 차이를
모르고 그대로 넣으면 웹에서 "미분류"로 뜨거나 RLS가 막을 수 있어서, 아래
CLASS_NAME_MAP에서 변환한다.

## 실행

    cd vision_조은수
    pip install -r requirements.txt   # ultralytics, opencv-python 등
    cp .env.example .env               # SUPABASE_URL / SUPABASE_ANON_KEY 채우기
    python detect_and_register.py --watch ../robot_이윤정/mock_controller/data/captures

이미지 한 장만 테스트하고 싶으면:

    python detect_and_register.py --image 아무사진.jpg
"""

import argparse
import os
import time
from collections import deque

from dotenv import load_dotenv
from ultralytics import YOLO

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "best.pt")
STORAGE_BUCKET = "lost-item-photos"

# TBD - 팀 협의 후 확정. 가이드 문서 예시값(0.6)을 기본으로 둠.
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.6"))

# TBD - 팀 협의 후 확정. 체크리스트에 "2~3회 연속 검출 확인 후"로 명시됨.
CONSECUTIVE_REQUIRED = int(os.environ.get("CONSECUTIVE_REQUIRED", "2"))

# TBD - 실제 순찰 구역 라벨 체계가 정해지면 교체.
DEFAULT_LOCATION = os.environ.get("DEFAULT_LOCATION", "A구역")

WATCH_INTERVAL_SEC = 3

# 같은 종류 물건이 짧은 시간 안에 여러 번 등록되는 걸 막는 쿨다운(초).
# 로봇이 장애물 감지→연속촬영을 여러 번 반복하면(테스트/재촬영 등) 매번
# 새 lost_items 행이 쌓이는 문제가 있어서(2026.08.30), 같은 item_type이
# 이 시간 안에 다시 조건을 채워도 재등록하지 않고 건너뛴다.
REGISTER_COOLDOWN_SEC = int(os.environ.get("REGISTER_COOLDOWN_SEC", "300"))

# 조은수 모델의 클래스 이름 -> 팀 Data Contract의 item_type 값.
# 모델이 재학습되어 클래스가 바뀌면 여기만 고치면 된다.
CLASS_NAME_MAP = {
    "backpack": "backpack",
    "wallet": "wallet",
    "waterbottle": "bottle",
}

_supabase_client = None


def _sb():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise RuntimeError(
                "SUPABASE_URL/SUPABASE_ANON_KEY가 .env에 없습니다 — "
                ".env.example을 .env로 복사하고 값을 채워주세요."
            )
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _supabase_client


def upload_and_register(image_path: str, item_type: str, confidence: float) -> dict:
    """
    사진을 Storage에 올리고 lost_items에 새 행을 등록한다.
    (store.py의 upload_capture()와 같은 패턴 — 버킷/정책이 이미 검증돼있음)
    """
    filename = os.path.basename(image_path)
    remote_path = f"lost_items/{filename}"
    with open(image_path, "rb") as f:
        data = f.read()

    _sb().storage.from_(STORAGE_BUCKET).upload(
        remote_path, data, {"content-type": "image/jpeg"}
    )
    image_url = _sb().storage.from_(STORAGE_BUCKET).get_public_url(remote_path)

    result = (
        _sb()
        .table("lost_items")
        .insert(
            {
                "image_url": image_url,
                "item_type": item_type,
                "confidence": confidence,  # 0~1 사이 숫자 (Data Contract 규칙)
                "location": DEFAULT_LOCATION,
                "status": "new",
                # description: Gemini 등 자연어 설명 생성은 아직 미구현(Task #10
                # 참고) — 지금은 비워둔다. 나중에 이 자리에 생성된 문장을 채우면 됨.
            }
        )
        .execute()
    )
    return result.data[0]


def detect(image_path: str, model: YOLO):
    """이미지 한 장에서 우리가 다루는 클래스 중 가장 신뢰도 높은 감지 결과 하나를 돌려준다."""
    results = model.predict(source=image_path, conf=CONFIDENCE_THRESHOLD, verbose=False)
    best = None
    for r in results:
        for box in r.boxes:
            raw_name = model.names[int(box.cls[0])]
            mapped = CLASS_NAME_MAP.get(raw_name)
            if mapped is None:
                continue  # 우리가 다루는 3종이 아니면 무시
            conf = float(box.conf[0])
            if best is None or conf > best[1]:
                best = (mapped, conf)
    return best  # (item_type, confidence) 또는 None


def run_watch(folder: str):
    print(
        f"[VISION] {folder} 감시 시작 (신뢰도>={CONFIDENCE_THRESHOLD}, 연속{CONSECUTIVE_REQUIRED}회 필요, "
        f"같은 종류 재등록 쿨다운 {REGISTER_COOLDOWN_SEC}초)"
    )
    model = YOLO(MODEL_PATH)

    seen_files = set()
    if os.path.isdir(folder):
        seen_files = set(os.listdir(folder))  # 이미 있던 파일은 새 파일로 취급 안 함

    last_class = None
    last_count = 0
    last_registered = {}  # item_type -> 마지막으로 등록한 시각(time.time())

    while True:
        try:
            if os.path.isdir(folder):
                for filename in sorted(os.listdir(folder)):
                    if filename in seen_files or not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                        continue
                    seen_files.add(filename)
                    path = os.path.join(folder, filename)

                    found = detect(path, model)
                    if found is None:
                        print(f"[VISION] {filename}: 감지 없음")
                        last_class, last_count = None, 0
                        continue

                    item_type, conf = found
                    if item_type == last_class:
                        last_count += 1
                    else:
                        last_class, last_count = item_type, 1

                    print(f"[VISION] {filename}: {item_type} (conf={conf:.2f}, 연속 {last_count}회)")

                    if last_count >= CONSECUTIVE_REQUIRED:
                        now = time.time()
                        last_time = last_registered.get(item_type)
                        if last_time is not None and now - last_time < REGISTER_COOLDOWN_SEC:
                            remaining = int(REGISTER_COOLDOWN_SEC - (now - last_time))
                            print(f"[VISION] {item_type} 쿨다운 중(재등록까지 {remaining}초) — 등록 건너뜀")
                        else:
                            row = upload_and_register(path, item_type, conf)
                            last_registered[item_type] = now
                            print(f"[VISION] lost_items 등록 완료: id={row.get('id')} item_type={item_type}")
                        last_class, last_count = None, 0  # 같은 물체를 반복 등록하지 않게 리셋
        except Exception as exc:
            # 다른 프로그램들과 동일한 원칙: 죽지 않고 로그 남기고 계속 시도
            print(f"[VISION] 처리 중 오류(다음 주기에 재시도): {exc}")

        time.sleep(WATCH_INTERVAL_SEC)


def main():
    parser = argparse.ArgumentParser(description="촬영 이미지를 YOLO로 분석해 Supabase에 자동 등록")
    parser.add_argument("--watch", help="감시할 이미지 폴더 경로")
    parser.add_argument("--image", help="이미지 한 장만 테스트 (Supabase 등록 없이 감지 결과만 출력)")
    args = parser.parse_args()

    if args.image:
        model = YOLO(MODEL_PATH)
        found = detect(args.image, model)
        print("감지 결과:", found if found else "없음")
    elif args.watch:
        run_watch(args.watch)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
