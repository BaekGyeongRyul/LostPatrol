# 03. 백경률 담당 진행 상황 — Web / Supabase / Git·GitHub

## 6-1. Web

React + Vite 기반 LostPatrol 관리자 웹사이트를 구현했습니다 (`web_백경률/`).

**주요 화면** (`src/pages/`)
- Dashboard
- Robot Control
- LivePatrol (실시간 순찰)
- Lost Items
- Lost Item Detail

자동순찰 명령 `patrol_start` / `patrol_stop`을 추가했고, 기존 수동 명령(forward/backward/left/right/stop/capture)과 자동순찰 명령이 웹 → Supabase(`robot_commands`)로 실제 전달되는 것까지 확인했습니다.

✅ 완료

## 6-2. Supabase

중앙 데이터 허브로 Supabase(`uityxtduglbshnvkstvx`)를 구성했습니다. 아래 컬럼/정책은 실제 `docs/02_SUPABASE_DATA_CONTRACT.md`와 코드를 확인한 내용입니다.

**주요 테이블**: `robot_commands`, `robot_status`, `lost_items`
**Storage**: `lost-item-photos` (public bucket)

### robot_commands

컬럼: `id, created_at, command, status(기본값 pending), executed_at`

웹에서 Forward 클릭 → `command=forward, status=pending` INSERT 확인 완료. 이후 추가한 `patrol_start` / `patrol_stop`도 동일하게 실제 Supabase INSERT 확인 완료.

✅ 완료

### robot_status

단일 행(id=1)의 `updated_at`을 heartbeat로 사용합니다.

- Raspberry Pi: 5초마다 `updated_at` 갱신
- Web: 마지막 `updated_at`이 15초 이상 갱신되지 않으면 OFFLINE 표시 (`web_백경률/src/lib/statusMap.js`, `ROBOT_OFFLINE_THRESHOLD_MS = 15000`)

실제 테스트에서 updated_at 갱신 시 ONLINE, 15초 이상 갱신이 없을 때 OFFLINE으로 전환되는 것을 확인했습니다. 이윤정 담당자의 Mock Robot Controller 연동에서도 웹사이트가 ONLINE으로 정상 표시되는 것을 확인했습니다.

✅ 완료

### lost_items

테스트용 우산 데이터를 DB에 넣었을 때 실제 웹 Lost Items 화면에서 우산 / 위치 / confidence / 상태가 표시되는 것을 확인했습니다. 웹에서 "반환 완료"를 선택했을 때 `status`가 `resolved`로 실제 UPDATE되는 것도 확인했습니다.

✅ 완료 (Web 표시/상태변경 기준. Vision 파이프라인의 자동 등록은 [05. 조은수 담당](05_조은수_Vision_YOLO.md) 참고)

## 6-3. Supabase 권한/RLS

초기에는 최소 권한 위주로 구성했으나, Raspberry Pi 담당자가 anon(publishable) key로 `robot_status`를 갱신하려다 권한 오류를 겪었고, 강사 피드백(신뢰된 디바이스라도 secret key 사용은 지양)에 따라 브라우저 밖 신뢰된 디바이스도 웹과 동일한 anon key만 쓰도록 방향을 정했습니다. 이에 따라 필요한 범위로 RLS 정책을 확장했습니다.

현재 코드(`robot_이윤정/mock_controller/store.py` 주석) 및 커밋 이력(`bb1d646`)으로 확인된 anon 권한:

| 테이블 | 확인된 anon 권한 |
|---|---|
| robot_commands | SELECT, INSERT, **UPDATE** (신규 추가) |
| robot_status | SELECT, **UPDATE** (신규 추가) |
| lost_items | SELECT, UPDATE |

DELETE는 개발 중 실수 방지를 위해 기본적으로 사용하지 않습니다.

이윤정 담당자가 겪었던 `robot_commands`/`robot_status` UPDATE RLS 오류는 위 정책 추가 후 해결되어, 실제 Supabase 연동(anon key 기준)에 성공했습니다.

✅ 완료 (robot_commands / robot_status anon UPDATE)

**⚠️ 팀 내 확인 필요**: `lost_items`에 대한 anon INSERT 권한 확장 여부는 `docs/02_SUPABASE_DATA_CONTRACT.md`에는 아직 "AI 파이프라인 INSERT는 anon 정책에 없고 service_role 필요"로 남아 있고, Vision 파이프라인 코드가 아직 저장소에 없어 실제 INSERT 테스트도 되지 않았습니다. Vision 연동 전에 anon INSERT로 갈지 service_role로 갈지 팀 협의가 필요합니다.

## 6-4. Supabase MCP + Claude Code

Claude Code와 Supabase MCP를 연결해, 요구사항과 변경 범위를 명확히 정의하고 이를 바탕으로 Claude Code를 이용해 기존 Supabase 프로젝트의 테이블/RLS 구조를 분석하고 필요한 부분만 수정·검증하는 방식으로 개발했습니다. 이를 통해 다음을 수행했습니다.

- 현재 테이블/RLS 구조 확인
- `patrol_start`/`patrol_stop` 명령 반영
- 기존 기능 유지 여부 확인
- Data Contract 문서 작성

✅ 완료

## 6-5. Git/GitHub 협업 환경

강사님 피드백에 따라 ZIP 파일 전달 방식 대신 Git/GitHub 기반 팀 협업 구조를 구축했습니다.

**공용 Repository**: `BaekGyeongRyul/LostPatrol`

**현재 최상위 폴더**: `00_실제_웹페이지`, `docs`, `robot_이윤정`, `vision_조은수`, `web_백경률`

각 팀원을 Collaborator로 초대해 하나의 공용 저장소에서 작업하도록 구성했습니다.

팀원별 개발 코드가 최종 통합 과정에서 충돌하지 않도록 공통 Data Contract 및 인터페이스 명세를 정의하고, 각 담당자가 동일한 명령어·DB 컬럼·상태값을 사용하도록 담당자별 개발 가이드와 Claude Code 작업 프롬프트를 작성했습니다.

`docs/`에 실제로 존재하는 문서:

- `00_README_FIRST.md` — 담당자별로 읽어야 할 문서 안내
- `01_SYSTEM_ARCHITECTURE.md` — 전체 시스템 구조
- `02_SUPABASE_DATA_CONTRACT.md` — Supabase Data Contract
- `03_INTEGRATION_TEST_CHECKLIST.md` — 통합 테스트 규격
- `04_ENV_AND_SECURITY_GUIDE.md` — 환경변수/보안 가이드
- `YOONJEONG_RAZBOT_GUIDE.md`, `YOONJEONG_CLAUDE_CODE_PROMPT.md` — Raspberry Pi 담당 가이드 및 프롬프트
- `EUNSOO_OPENCV_ROBOFLOW_GUIDE.md`, `EUNSOO_CLAUDE_CODE_PROMPT.md` — Vision 담당 가이드 및 프롬프트
- `TEAM_INTEGRATION_GUIDE.md` — 연동 요약본

✅ 완료

## 6-6. GitHub Pages

GitHub Actions(`.github/workflows/deploy-pages.yml`) + GitHub Pages를 이용해 로컬 PC에서만 실행되던 웹을 실제 URL로 배포했습니다. `main` 브랜치에 push되면 `web_백경률`을 빌드해 자동 배포됩니다.

**Live Web**: https://BaekGyeongRyul.github.io/LostPatrol/

팀원 및 강사님이 별도 개발환경 없이 URL만으로 실제 LostPatrol 웹사이트에 접속할 수 있습니다. 저장소 최상위에 `00_실제_웹페이지` 폴더를 추가해 실제 웹사이트 링크를 쉽게 찾을 수 있도록 했습니다.

✅ 완료
