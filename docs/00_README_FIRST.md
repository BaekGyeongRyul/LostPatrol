# 00. README FIRST — 팀원은 이 파일부터 읽으세요

이 폴더(`LostPatrol_TEAM_HANDOFF`)는 LostPatrol 프로젝트를 각자 담당 파트에서 연결하기 위해 필요한 모든 것을 담은 전달용 패키지입니다. 이 폴더만 있으면 최종 웹사이트를 열어볼 수 있고, Supabase 연동 규격을 확인할 수 있고, 자기 코드를 어떻게 연결할지 안내를 받을 수 있습니다.

## 이 폴더에서 최종 웹사이트를 바로 보고 싶다면

`FINAL_WEB/dist-share/index.html` 을 더블클릭해서 브라우저로 열면 지금까지 확정된 최종 웹사이트를 그대로 볼 수 있습니다 (실제 Supabase에 연결되어 있어 실시간 데이터가 뜹니다).

## 담당자별로 무엇을 읽어야 하는지

### 이윤정 (Raspberry Pi / Razbot 담당)

1. `02_SUPABASE_DATA_CONTRACT.md` — 어떤 테이블에 어떤 값을 어떻게 넣고 읽어야 하는지
2. `YOONJEONG_RAZBOT_GUIDE.md` — Pi 코드로 옮기는 구체적인 방법
3. `YOONJEONG_CLAUDE_CODE_PROMPT.md` — 본인 프로젝트 폴더에서 Claude Code에 그대로 붙여넣을 프롬프트
4. `03_INTEGRATION_TEST_CHECKLIST.md`의 1~9번 항목으로 최종 확인

### 조은수 (OpenCV / Roboflow / YOLO 담당)

1. `02_SUPABASE_DATA_CONTRACT.md` — 어떤 테이블에 어떤 값을 어떻게 넣어야 하는지
2. `EUNSOO_OPENCV_ROBOFLOW_GUIDE.md` — AI 파이프라인을 Supabase에 연결하는 구체적인 방법
3. `EUNSOO_CLAUDE_CODE_PROMPT.md` — 본인 프로젝트 폴더에서 Claude Code에 그대로 붙여넣을 프롬프트
4. `03_INTEGRATION_TEST_CHECKLIST.md`의 10~11번 항목으로 최종 확인

### 웹/Supabase 담당자 (참고용, 이미 구현 완료)

- `01_SYSTEM_ARCHITECTURE.md`, `TEAM_INTEGRATION_GUIDE.md`, `04_ENV_AND_SECURITY_GUIDE.md`를 팀원들에게 안내할 때 참고하세요.

## 전체 파일 구성

| 파일/폴더 | 내용 |
|---|---|
| `01_SYSTEM_ARCHITECTURE.md` | 전체 시스템 구조, 현재 검증된 기능, 아직 안 된 부분, 발견된 RLS 권한 이슈 |
| `02_SUPABASE_DATA_CONTRACT.md` | 실제 Supabase 테이블/컬럼/RLS를 읽기 전용으로 확인한 최종 데이터 규격 |
| `03_INTEGRATION_TEST_CHECKLIST.md` | 최종 통합 테스트 12개 항목 (담당자/체크박스 포함) |
| `04_ENV_AND_SECURITY_GUIDE.md` | Public key vs Secret key 구분, .env 규칙, 이번 패키지 Secret 검사 결과 |
| `TEAM_MESSAGE.md` | 팀 단체방에 바로 복붙할 공지 메시지 |
| `TEAM_INTEGRATION_GUIDE.md` | 기존에 작성된 연동 요약본 (참고용) |
| `YOONJEONG_RAZBOT_GUIDE.md` | 이윤정 담당 — Raspberry Pi/Razbot 연동 상세 가이드 |
| `YOONJEONG_CLAUDE_CODE_PROMPT.md` | 이윤정용 — 그대로 복붙하는 Claude Code 프롬프트 |
| `EUNSOO_OPENCV_ROBOFLOW_GUIDE.md` | 조은수 담당 — OpenCV/Roboflow/YOLO 연동 상세 가이드 |
| `EUNSOO_CLAUDE_CODE_PROMPT.md` | 조은수용 — 그대로 복붙하는 Claude Code 프롬프트 |
| `FINAL_WEB/dist-share/index.html` | 최종 확정 웹사이트 (더블클릭으로 바로 열기) |
| `FINAL_WEB/SOURCE/` | 최종 웹사이트(`web-redesign`)의 실행/참고용 소스 사본 (구버전 `web` 폴더 아님) |
| `ENV_EXAMPLE/.env.example` | 값이 비어있는 환경변수 템플릿 (실제 키 없음) |

## 절대 지켜야 할 규칙 (모든 담당자 공통)

- `robot_commands.command` 8종, `lost_items.item_type` 3종, `lost_items.status` 5종, 테이블/컬럼 이름은 **임의로 변경 금지**. 변경이 필요하면 코드부터 고치지 말고 팀과 먼저 상의하세요.
- `left`/`right`는 반드시 **제자리 좌/우회전**입니다 (전진하며 도는 것 아님).
- heartbeat는 **5초**, 웹 OFFLINE 판정은 **15초**입니다.
- `service_role` key(있으면 무엇이든 RLS를 우회할 수 있는 키)는 **절대 웹 코드나 Git에 넣지 않습니다.** 각자 로컬 `.env`에만 둡니다.
- 장애물 정지 거리(cm)는 아직 **TBD**(팀 협의 후 확정)입니다. 확정값처럼 코드에 박아넣지 마세요.
