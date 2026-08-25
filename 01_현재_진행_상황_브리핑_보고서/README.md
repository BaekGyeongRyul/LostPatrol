# LostPatrol 현재 진행 상황 브리핑

작성 기준: 2026년 8월 25일 기준

## 현재 한 줄 상태

Web–Supabase–Robot(Mock Controller) 간 기본 소프트웨어 연동은 실제 DB 데이터로 확인되었으며, 현재 Vision 3종 모델 학습·로컬 추론과 실제 하드웨어(Razbot)·카메라·Storage 이미지 업로드 통합을 진행 중입니다. 실제 로봇 하드웨어와 Vision 파이프라인까지 포함한 최종 통합은 아직 완료 전 단계입니다.

## 담당별 현재 상태

**백경률** — Web / Supabase / GitHub / Pages / Data Contract
✅ Web 관제 대시보드 구현, Supabase 연동, GitHub 협업 구조, GitHub Pages 배포, Data Contract 문서화

**이윤정** — Raspberry Pi / Razbot
✅ Mock Robot Controller, Supabase 연동(anon key), Heartbeat, 순찰 상태머신, 버그 3건 수정
🔄 Storage 이미지 업로드(현재 403 권한 오류로 미해결), 실제 Razbot 하드웨어 연동

**조은수** — Vision / YOLO
✅ 기술 스택 결정(YOLO+OpenCV, Roboflow), 가방 데이터 수집·라벨링, 가방 1종 YOLO 학습
🔄 로컬 추론 전환, 우산·물병 데이터 수집, 3종 모델 학습, Supabase 연동

## 바로가기

- [01. 전체 진행상황](01_프로젝트_전체_진행상황.md)
- [02. 강사님 및 팀원 피드백 반영사항](02_강사님_및_팀원_피드백_반영사항.md)
- [03. 백경률 담당 — Web/Supabase/GitHub](03_백경률_Web_Supabase_GitHub.md)
- [04. 이윤정 담당 — Raspberry Pi/Razbot](04_이윤정_RaspberryPi_Razbot.md)
- [05. 조은수 담당 — Vision/YOLO](05_조은수_Vision_YOLO.md)
- [06. 현재 시스템 연동 현황](06_현재_시스템_연동_현황.md)
- [07. 남은 과제 및 우선순위](07_남은_과제_및_우선순위.md)
- [08. 최종 통합 테스트 계획](08_최종_통합_테스트_계획.md)

Live Web: https://BaekGyeongRyul.github.io/LostPatrol/
