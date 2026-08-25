# 05. 조은수 담당 진행 상황 — Vision / YOLO

담당: Python, Vision, OpenCV, Roboflow, YOLO, Object Detection

> 아래 내용은 조은수 담당자가 직접 전달한 진행 상황입니다. 현재 저장소의 `vision_조은수/` 폴더에는 안내용 README만 있고, 실제 코드/데이터셋/학습된 모델 파일은 아직 GitHub에 commit/push되지 않았습니다. 로컬 작업 및 진행 상황을 그대로 정리하되, 코드 기준으로 검증된 항목이 아님을 밝힙니다.

## ✅ 완료

- **AI 이미지 인식 방식 결정**: YOLO + OpenCV 사용
- **Gemini API**: 사용하지 않기로 결정
- **Dataset / Labeling 도구**: Roboflow 사용, 배경 제거(누끼) 방식이 아니라 Object Detection용 Bounding Box 라벨링 방식 채택
- **객체 종류 최종 결정**: 가방 / 우산 / 물병 3종 (팀 Data Contract와 동일)
- Roboflow 추론 서버 오류 발생 확인 → 서버 추론 의존 대신 학습 모델을 내려받아 로컬 Python 추론 방식으로 전환 결정
- **가방/우산/물병 3종 클래스 구별 가능한 모델 구축** (조은수 담당자 보고 기준, 2026.08.25): 우산·물병 데이터 수집·라벨링과 3종 재학습을 마쳐, 세 클래스를 서로 구분할 수 있는 상태까지 확인했습니다.

## 🔄 진행 중 / 남은 작업

1. **Razbot 카메라 실제 연동** — 사진/PC Webcam 테스트 다음 단계로, 팀 협의로 확정된 Razbot 카메라 1대를 실제 입력으로 연결 ([04. 이윤정 담당](04_이윤정_RaspberryPi_Razbot.md) 참고)
2. **Raspberry Pi에서 YOLO 추론 실행** — PC에서 학습, Raspberry Pi에서 추론하는 방향으로 진행 예정
3. **confidence / Bounding Box 실제 환경 검증** — Razbot 카메라 입력 기준으로 재확인
4. **분실물 후보 판단 로직** — 일정 confidence 이상, 동일 객체가 일정 프레임/시간 동안 반복 검출 시 후보로 확정. 팀 논의에서는 2~3회 연속 검출을 검토했으나 confidence 임계값과 연속 검출 횟수 모두 아직 최종 확정값은 아닙니다.
5. **동일 물체 반복 검출/중복 등록 방지** — 후보 판단 로직과 함께 설계 필요
6. **Supabase 연동** — 물체 종류/confidence/사진/시간/위치/status를 `lost_items` Data Contract에 맞춰 저장. `lost_items` anon INSERT는 이윤정 담당자 테스트로 이미 확인되었고, `lost-item-photos` Storage도 anon SELECT/INSERT/UPDATE 환경이 준비되어 있어([04. 이윤정 담당](04_이윤정_RaspberryPi_Razbot.md) 참고) Vision 쪽에서 바로 사용 가능합니다. 다만 Vision 쪽의 실제 업로드/자동등록은 아직 진행 전입니다.
7. **Web 실제 표시 확인** — 위 자동등록 이후 Lost Items 화면에서 실제 탐지 결과가 뜨는지 확인
8. **최종 통합** — Razbot Camera → Raspberry Pi/Vision → OpenCV → YOLO → 분실물 후보 판단 → Supabase → LostPatrol Web

## ⚠️ 팀 내 확인 필요

- **class명 표기**: 팀 Data Contract(`docs/02_SUPABASE_DATA_CONTRACT.md`)의 `lost_items.item_type` 값은 `backpack`으로 고정되어 있습니다. Vision 쪽 코드가 아직 저장소에 없어, 실제 사용하는 class명이 `bag`인지 `backpack`인지는 최종 통합 전 반드시 Data Contract와 일치시켜야 합니다.
- **confidence threshold 및 연속 검출 횟수**: 현재 `docs/EUNSOO_OPENCV_ROBOFLOW_GUIDE.md`에는 예시값(confidence 0.6 이상, 2~3회 연속 검출)이 안내되어 있으나 팀이 조정 가능한 값으로 명시되어 있고, 아직 최종 확정되지 않았습니다.

카메라 입력 장치는 2026.08.25 팀 협의로 Razbot 카메라 1대 사용으로 정리되어([04. 이윤정 담당](04_이윤정_RaspberryPi_Razbot.md) 참고) 더 이상 확인 필요 항목이 아닙니다.
