# OpenCV / Roboflow / YOLO 연동 가이드 (담당: 조은수)

담당 범위: OpenCV, Roboflow, YOLO, Dataset 구성, 분실물 객체 감지, AI 추론, Supabase `lost_items` 연동.

먼저 `02_SUPABASE_DATA_CONTRACT.md`를 읽고 오세요. 이 문서는 그 내용을 실제 AI 파이프라인 코드로 어떻게 옮길지에 대한 실행 가이드입니다.

## 0. 준비물

- Supabase 프로젝트 URL: `https://uityxtduglbshnvkstvx.supabase.co`
- **`service_role` key** (Supabase 대시보드 > Project Settings > API에서 본인이 직접 확인)
- 이유: `lost_items`에는 anon key로 하는 INSERT 정책이 없고(웹의 상태 UPDATE만 허용), `storage.objects`(사진 버킷)에는 RLS 정책이 아예 없어서 anon key로 업로드 자체가 불가능합니다. 신뢰된 백엔드/디바이스 코드이므로 `service_role` key를 로컬 `.env`에만 저장해서 사용하세요.

## 1. 대상 클래스 (정확히 3종, 고정)

| DB에 저장할 값 (`item_type`) | 웹에서 보여줄 이름 |
|---|---|
| `umbrella` | 우산 |
| `bottle` | 물병 |
| `backpack` | 가방 |

DB/코드에는 반드시 영문 문자열(`umbrella`/`bottle`/`backpack`) 그대로 저장하고, 한글 표시는 웹이 알아서 매핑합니다. 새 클래스를 임의로 추가하지 마세요.

## 2. Roboflow 데이터셋 구성

- **Object Detection** 프로젝트로 만드세요 (Classification/Segmentation 아님).
- 라벨링 방식은 **Bounding Box**입니다. 배경을 지워서 누끼를 따는 방식(Segmentation/matting)은 기본 요구사항이 아닙니다.
- 각 클래스별로 **다양한 배경, 각도, 거리, 조명**에서 촬영한 이미지를 준비하세요.
- 연속 촬영한 거의 동일한 프레임(예: 가만히 둔 물건을 1초 간격으로 30장 찍은 것)만 대량으로 넣는 것은 피하세요 — 실질적으로 같은 데이터를 중복시키는 것이라 일반화 성능이 떨어집니다.

## 3. YOLO 학습 → OpenCV 추론 연결

- Roboflow에서 export한 데이터셋으로 YOLO(예: YOLOv8) 학습
- 학습된 모델을 OpenCV 카메라 스트림(또는 Raspberry Pi 카메라 프레임)에 연결해서 실시간/주기적 추론
- 추론 결과의 confidence는 **0~1 사이 float 그대로** 사용하세요. DB에도 이 값을 그대로 저장합니다(웹이 `* 100`으로 표시하므로 정수 퍼센트로 바꿔서 저장하면 안 됩니다).

## 4. 오탐 방지: 연속 검출 확인

한 프레임에서 감지됐다고 바로 분실물로 확정하지 마세요. 다음 조건을 만족할 때만 "분실물 후보"로 확정합니다:

- **동일 객체가 2~3회 연속으로 검출**되고
- 각 검출의 confidence가 정해둔 기준(예: 0.6 이상 — 팀에서 실제 값을 조정)을 만족할 때

의사코드:

```python
detection_streak = {}  # {class_name: 연속 검출 횟수}
CONFIDENCE_THRESHOLD = 0.6  # 팀에서 조정 가능한 값
REQUIRED_STREAK = 2  # 2~3회 중 우선 2로 시작, 필요시 조정

def on_frame_detections(detections):
    seen_this_frame = set()
    for det in detections:
        cls, conf = det["class"], det["confidence"]
        if cls not in ("umbrella", "bottle", "backpack"):
            continue
        seen_this_frame.add(cls)
        if conf >= CONFIDENCE_THRESHOLD:
            detection_streak[cls] = detection_streak.get(cls, 0) + 1
        else:
            detection_streak[cls] = 0

        if detection_streak[cls] >= REQUIRED_STREAK:
            confirm_lost_item(cls, conf)
            detection_streak[cls] = 0  # 중복 등록 방지 위해 리셋

    # 이번 프레임에 안 보인 클래스는 streak 리셋
    for cls in list(detection_streak):
        if cls not in seen_this_frame:
            detection_streak[cls] = 0
```

## 5. 중복 분실물 등록 방지 아이디어

같은 물건을 계속 찍어서 `lost_items`에 중복으로 여러 번 INSERT되는 것을 막기 위한 아이디어(팀과 상의해서 적용 수준 결정):

- 마지막으로 같은 `item_type`을 등록한 시각을 기억해두고, 일정 시간(예: 수 분) 이내에는 재등록하지 않기
- 같은 위치(`location`)에서 최근 등록된 동일 `item_type` 항목이 아직 `status='new'`(미확인)면 새로 만들지 않고 스킵

## 6. Capture → Storage 업로드 → lost_items 등록 흐름

가능한 최종 흐름(Plan A):

```
자동순찰 → Camera → OpenCV/YOLO → umbrella/bottle/backpack 탐지
→ 2~3회 연속 검출 확인 → 로봇 정지 → Capture
→ lost-item-photos Storage 업로드 → lost_items 등록 → 필요 시 일정 시간 후 순찰 재개
```

```python
def confirm_lost_item(item_type, confidence, frame):
    # 1) 사진 저장
    file_bytes = encode_frame_to_jpeg(frame)
    file_path = f"{item_type}/{uuid4()}.jpg"
    supabase.storage.from_("lost-item-photos").upload(file_path, file_bytes)
    image_url = supabase.storage.from_("lost-item-photos").get_public_url(file_path)

    # 2) lost_items 등록
    supabase.table("lost_items").insert({
        "item_type": item_type,          # umbrella / bottle / backpack
        "confidence": round(confidence, 4),  # 0~1 사이 float 그대로
        "image_url": image_url,
        "location": current_zone_name,   # 로봇의 현재 순찰 구역
        "status": "new",                 # 초기값 고정
        # description: 필수 아님. 자동 생성 문구를 넣고 싶으면 넣어도 되고, 없으면 비워둬도 됨.
    }).execute()
```

- `status`는 항상 초기값 `new`로 등록하세요. 이후 상태 변경(보관 중/반환 완료/반려)은 웹 관리자가 수동으로 처리합니다.
- `description`은 필수 컬럼이 아닙니다. 자동 생성 문구(예: "A구역에서 탐지됨")를 넣어도 되고 비워둬도 됩니다.

## 7. Plan B (시간이 부족할 경우 백업 방법)

2일 안에 구현해야 하는 프로젝트이므로, 실시간 자동 Capture + 연속 검출 로직이 기한 내 어려우면 이 기능이 전체 프로젝트를 막아서는 안 됩니다. 아래처럼 단순화한 방식을 백업으로 사용하세요:

```
정해진 순찰 지점에 도착 → 그 자리에서 Capture(정지 사진 1장)
→ YOLO로 그 사진 분석 → 대상 클래스 탐지되면 바로 lost_items 등록
```

- 실시간 스트리밍/연속 프레임 판단 없이, 정지된 순찰 지점에서 사진 한 장을 찍어 분석하는 방식이라 구현이 훨씬 단순합니다.
- 이 경우에도 `item_type`/`confidence`/`image_url`/`location`/`status` 규격은 동일하게 지킵니다.

## 8. Web과 연결 테스트 방법

1. 스크립트/노트북에서 임의의 umbrella/bottle/backpack 사진으로 위 4~6번 로직을 한 번 실행
2. Supabase Table Editor에서 `lost_items`에 새 행이 `status='new'`로 잘 들어갔는지 확인
3. Storage `lost-item-photos` 버킷에 파일이 올라갔는지, 공개 URL이 브라우저에서 바로 열리는지 확인
4. 웹(`FINAL_WEB/dist-share/index.html` 또는 `web-redesign` dev 서버)의 Lost Items 목록에서 방금 등록한 항목이 사진과 함께 보이는지 확인
5. 웹에서 상태를 "보관 중"으로 바꿔보고 `lost_items.status`가 실제로 바뀌는지 확인 (이미 검증된 기능이라 회귀 확인 목적)

자세한 체크리스트는 `03_INTEGRATION_TEST_CHECKLIST.md`를 사용하세요. 바로 붙여넣어 쓸 수 있는 작업 프롬프트는 `EUNSOO_CLAUDE_CODE_PROMPT.md`에 있습니다.
