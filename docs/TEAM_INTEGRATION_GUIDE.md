# TEAM_INTEGRATION_GUIDE

로봇(Raspberry Pi) · 웹(web-redesign) · OpenCV/YOLO 담당자가 공유하는 Supabase 연동 규격입니다.
실사용 웹 프로젝트는 `web-redesign` 폴더이며, Supabase 프로젝트는 `uityxtduglbshnvkstvx` 입니다.

## Robot Commands

`robot_commands.command` 에 들어갈 수 있는 값(anon INSERT RLS로 강제됨):

| command        | 의미                     |
|----------------|--------------------------|
| forward        | 직진                     |
| backward       | 후진                     |
| left           | 제자리 좌회전            |
| right          | 제자리 우회전            |
| stop           | 즉시 정지                |
| capture        | 카메라 촬영              |
| patrol_start   | 라인트레이싱 자동순찰 시작 |
| patrol_stop    | 자동순찰 종료            |

`left`/`right`는 반드시 "제자리 좌/우회전" 의미로 사용합니다 (조향이 아님).

## robot_commands 테이블

컬럼: `id, created_at, command, status(default: pending), executed_at`

- **Web**: `command`, `status: 'pending'` 로 INSERT만 수행합니다. (status 기본값을 그대로 사용)
- **Raspberry Pi**:
  1. `status = 'pending'` 인 명령을 SELECT
  2. 실제 동작 실행
  3. 완료 후 해당 row의 `status`(예: `done`), `executed_at` UPDATE

RLS 요약:
- `anon_read_robot_commands`: anon SELECT 허용 (전체)
- `anon_insert_robot_commands`: anon INSERT 허용, 단 `command`가 위 8개 값 중 하나이고 `status = 'pending'` 인 경우만 허용

## robot_status 테이블

컬럼: `id, state(default: idle), last_command, updated_at(default: now())`

- **Raspberry Pi**: `state`, `last_command`, `updated_at` 을 주기적으로 UPDATE
  - heartbeat 주기: **5초마다** `updated_at` 갱신
- **Web**: `updated_at` 기준으로 ONLINE/OFFLINE 판단
  - 마지막 `updated_at`이 **15초 이상** 지나면 OFFLINE으로 표시
  - 구현 위치: `web-redesign/src/lib/statusMap.js` (`ROBOT_OFFLINE_THRESHOLD_MS = 15000`, `isRobotOffline()`)
  - 확인 결과 현재 웹 구현이 이 규격과 일치하여 별도 수정하지 않았습니다.

## Lost Item Classes

- `umbrella` (우산)
- `bottle` (물병)
- `backpack` (가방/백팩)

(웹 필터/라벨에는 `handbag`, `suitcase` 도 표시 옵션으로 존재하지만, 현재 탐지 파이프라인이 다루는 핵심 클래스는 위 3종입니다.)

## lost_items 테이블

컬럼: `id, image_url, item_type, description, confidence, detected_at, location, status(default: pending_analysis), created_at`

OpenCV/YOLO 담당자가 탐지 확정 후 저장할 데이터:

- `item_type` — 위 Lost Item Classes 중 하나
- `confidence` — **0~1 사이의 숫자**로 저장 (예: `0.91` = 웹에서 91%로 표시)
- `image_url` — Storage에 업로드된 이미지 URL
- `location` — 탐지 위치
- `status` — 초기값은 `new` 사용 (웹의 "확인 필요" 상태로 표시됨)

이후 웹에서 사람이 상태를 `confirmed`(보관 중) / `resolved`(반환 완료) / `rejected`(반려) 로 변경할 수 있습니다.

## Storage

- bucket: `lost-item-photos`

## 안전 규칙 (절대 하지 말 것)

- 기존 테이블 DROP
- 기존 데이터 삭제
- Supabase 프로젝트 reset / `db reset`
- Secret Key를 소스코드에 작성
- `.env.local` 을 Git에 추가 (`.gitignore`에 이미 `*.env.*` 패턴으로 제외되어 있음)
- 정상 작동 중인 RLS를 전부 제거
- 기존 웹 디자인을 임의로 재디자인
