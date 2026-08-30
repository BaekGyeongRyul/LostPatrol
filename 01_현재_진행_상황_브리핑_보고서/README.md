# LostPatrol 현재 진행 상황 브리핑

작성 기준: 2026년 8월 30일 기준

## 현재 한 줄 상태

Web–Supabase–Robot Controller/Safety Monitor 연동, Vision 3종(가방/우산/물병) 객체 분류 모델, 실제 Razbot 하드웨어(모터·카메라·초음파·라인트레이싱·안전센서·로봇 얼굴) 통합, 장애물 감지→분실물 자동등록 엔드투엔드 파이프라인까지 완료되었으며, 시연 영상 5장면(웹 제어/자동순찰/장애물감지/분실물등록/화재·소음경보) 촬영까지 마쳤습니다.

## 담당별 현재 상태

**백경률** — Web / Supabase / GitHub / Pages / Data Contract
✅ Web 관제 대시보드 구현, Supabase 연동, GitHub 협업 구조, GitHub Pages 배포, Data Contract 문서화, 안전센서용 신규 테이블(`safety_status`/`patrol_events`) 구축(2026.08.25)

**이윤정** — Raspberry Pi / Razbot
✅ Mock Robot Controller부터 실물 하드웨어(모터·카메라·초음파·라인트레이싱·아두이노 안전센서·ESP32 로봇 얼굴) 전체 통합 완료. 자동순찰 조향 로직 개선(직각 코너 대응), 장애물 감지→후진→촬영→분실물 자동등록 엔드투엔드 파이프라인 완성, GPIO 자동시작 충돌 영구 해결, 시연 영상 5장면 촬영 완료(2026.08.26~30, 상세는 [04번 문서](04_이윤정_RaspberryPi_Razbot.md) 참고)
🔄 초음파 센서 신호 안정화, 온도센서 교체 여부 협의

**조은수** — Vision / YOLO
✅ 기술 스택 결정(YOLO+OpenCV, Roboflow, Bounding Box), 가방/우산/물병 3종 클래스 구별 가능한 모델 구축(담당자 보고 기준, 2026.08.25)
🔄 Razbot Camera 실제 연동, Raspberry Pi 추론, 분실물 후보 판정 로직, Supabase(lost_items/Storage) 자동 연동

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
