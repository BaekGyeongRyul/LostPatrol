# 조은수 — Claude Code 작업 프롬프트 (그대로 복붙해서 사용)

아래 내용을 본인의 OpenCV / Roboflow / YOLO 프로젝트 폴더를 VS Code로 열고, Claude Code에게 그대로 붙여넣으세요.

---

```
나는 LostPatrol이라는 팀 프로젝트의 OpenCV/Roboflow/YOLO 담당자야.
분실물(우산/물병/가방) 탐지 결과를 Supabase에 연동해야 해.

먼저 아래 작업을 해줘:

1. 지금 이 폴더의 기존 AI 프로젝트 구조를 조사해줘.
   - Roboflow dataset이 어디 있는지, 어떤 형식인지
   - 학습된 YOLO 모델이 있는지, 어디 있는지
   - OpenCV로 카메라/영상 입력을 어떻게 받고 있는지
   먼저 파악하고 나한테 요약해줘. 아직 아무것도 수정하지 마.

2. 조사 후에는 기존 코드/모델을 최대한 재사용하면서,
   Supabase 연동 레이어(Storage 업로드 + DB INSERT)를 추가해줘.

대상 클래스는 정확히 3종류뿐이야. 이 문자열 그대로 써야 해:
- umbrella (우산)
- bottle (물병)
- backpack (가방)
다른 클래스를 임의로 추가하거나 이름을 바꾸지 마.

[Roboflow 데이터셋]
- Object Detection(Bounding Box) 방식이야. 배경 제거/누끼 따기는 기본 요구사항이 아니야.
- 데이터는 다양한 배경/각도/거리/조명으로 구성하고, 거의 동일한 연속 프레임만
  대량으로 쓰는 건 피해야 해. (이미 있는 데이터셋을 검토해서 이 기준에 맞는지
  확인하고, 문제 있으면 나한테 알려줘.)

[YOLO + OpenCV 추론]
- confidence는 0~1 사이 float 그대로 유지해줘. 정수 퍼센트(예: 91)로 변환하지 마.
  나중에 웹이 confidence * 100으로 퍼센트를 표시하기 때문에, DB에는 반드시
  0.91 같은 소수로 저장해야 해.

[오탐 방지 - 연속 검출 확인]
- 한 프레임에서 감지됐다고 바로 확정하지 말고, 동일 객체가 2~3회 연속으로
  검출되고 confidence 기준을 만족할 때만 "분실물 후보"로 확정하는 로직을 넣어줘.
- 같은 물건이 계속 잡혀서 lost_items에 중복으로 여러 번 등록되지 않도록
  간단한 쿨다운/중복 방지 로직도 추가해줘 (예: 최근 등록한 같은 item_type은
  일정 시간 동안 재등록하지 않기).

[Capture → Storage 업로드]
- 확정된 순간의 프레임을 이미지로 저장하고, Supabase Storage 버킷
  "lost-item-photos"에 업로드한 뒤 공개 URL을 받아와줘.

[lost_items 테이블 INSERT] 컬럼: id, image_url, item_type, description, confidence,
detected_at, location, status, created_at
- item_type: umbrella / bottle / backpack 중 하나
- confidence: 0~1 사이 float
- image_url: Storage 업로드 후 받은 공개 URL
- location: 현재 순찰 구역/위치 (문자열, 있는 만큼만)
- status: 항상 초기값 "new"로 고정해서 넣어줘 (다른 값 넣지 마. 이후 상태 변경은
  웹 관리자가 수동으로 함)
- description: 필수 아님. 없으면 비워둬도 되고, 자동 생성 문구를 넣어도 됨.

절대 하지 말아야 할 것:
- 웹이 이미 쓰고 있는 기존 데이터 구조(테이블/컬럼 이름, item_type/status 문자열)를
  임의로 바꾸지 마. 바꿔야 할 것 같으면 나한테 먼저 물어봐.
- DB 컬럼 이름을 새로 만들거나 이름을 바꾸지 마.

[연결 정보]
- SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY는 .env 파일에서 읽어와줘.
  (.env는 내가 직접 만들 것이고, 이 프롬프트에는 실제 키 값이 없어.
   .env를 .gitignore에 반드시 추가해줘. service_role key를 코드에 직접 쓰지 마.)
- service_role key를 쓰는 이유: lost_items에는 anon key로 하는 INSERT 정책이 없고,
  storage.objects(사진 버킷)에는 RLS 정책이 아예 없어서 anon key로는 업로드가
  안 되기 때문이야. 신뢰된 백엔드 코드니까 service_role key로 우회한다.

[시간이 부족할 경우 Plan B도 코드에 옵션으로 남겨줘]
- 실시간 스트리밍 + 연속 검출 로직이 기한(2일) 안에 다 구현되기 어려우면,
  "정해진 순찰 지점에서 사진 한 장 Capture → YOLO 분석 → 탐지되면 바로 등록"하는
  단순한 방식도 같이 만들어줘. 이건 2~3회 연속 검출 없이 그냥 그 한 장으로 판단하는
  더 단순한 버전이야. 이 기능 때문에 전체 프로젝트가 막히면 안 되니까, 시간이
  부족하면 이 Plan B를 기본으로 켜둬도 괜찮아.

- 실제 Raspberry Pi 카메라(피카메라 또는 USB 카메라) 환경에서 돌아갈 수 있게
  카메라 입력 부분은 너무 특정 환경에만 종속되지 않게 만들어줘.

구현이 끝나면 아래를 나한테 보고해줘:
1. 수정/추가한 파일 목록
2. 연속 검출 로직과 중복 방지 로직이 실제로 어떻게 동작하는지 요약
3. 내가 직접 테스트해볼 수 있는 방법 (샘플 이미지로 실행하는 방법,
   Supabase Table Editor/Storage에서 어떤 걸 확인하면 되는지 포함)
```
