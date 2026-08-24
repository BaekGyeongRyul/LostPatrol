# 02. SUPABASE DATA CONTRACT

이 문서는 Supabase MCP로 실제 프로젝트를 **읽기 전용**으로 조회해서 검증한 현재 스키마/RLS 기준입니다. 여기 적힌 테이블명, 컬럼명, command 문자열, class 문자열은 **팀 전체 협의 없이 임의로 변경하지 않습니다.**

Supabase 프로젝트: `uityxtduglbshnvkstvx` (URL: `https://uityxtduglbshnvkstvx.supabase.co`)

---

## robot_commands

| 컬럼 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| id | bigint (identity) | 자동증가 | PK |
| created_at | timestamptz | now() | |
| command | text | (없음) | 아래 8종 중 하나 |
| status | text | `'pending'` | |
| executed_at | timestamptz | NULL | Pi가 실행 완료 시 채움 |

### command 허용 값 (8종, 고정)

| command | 의미 |
|---|---|
| `forward` | 직진 |
| `backward` | 후진 |
| `left` | **제자리 좌회전** (전진하며 좌회전 아님) |
| `right` | **제자리 우회전** (전진하며 우회전 아님) |
| `stop` | 즉시 정지 |
| `capture` | 카메라 촬영 |
| `patrol_start` | 라인트레이싱 기반 자동순찰 시작 |
| `patrol_stop` | 자동순찰 종료 |

### 흐름

- **Web**: `{ command, status: 'pending' }` INSERT만 수행 (status는 DB 기본값 사용)
- **Raspberry Pi**:
  1. `status = 'pending'` 인 행을 SELECT (polling)
  2. 실제 로봇 동작 실행
  3. 완료 후 해당 행을 UPDATE: `status`, `executed_at`

### status 값 컨벤션

- `pending` — 대기 중 (DB 기본값, 웹이 INSERT 시 사용)
- `done` — 실행 완료. **이미 존재하는 컨벤션**(웹 mock 코드 `mockStore.js`에서 사용 중인 값)을 그대로 따릅니다. DB에 CHECK 제약은 없지만 임의로 다른 값을 새로 만들지 마세요.
- 실행 실패(에러) 시 어떤 status를 쓸지는 **아직 팀에서 정한 값이 없습니다.** 새 값을 혼자 정하지 말고, 우선 `done`으로 두고 실패 사실은 `robot_status.state`(예: `camera_error`)나 별도 로그로 남긴 뒤 팀과 상의하세요.

### RLS (현재 실제 정책, 읽기 전용 확인)

- `anon_read_robot_commands` — SELECT, 전체 허용
- `anon_insert_robot_commands` — INSERT, `command`가 위 8종 중 하나이고 `status='pending'`일 때만 허용
- **UPDATE 정책 없음** — anon(publishable) key로는 status/executed_at을 갱신할 수 없습니다. Pi는 `service_role` key 사용 권장 (`01_SYSTEM_ARCHITECTURE.md`, `04_ENV_AND_SECURITY_GUIDE.md` 참고)

---

## robot_status

단일 행(`id = 1`)을 계속 UPDATE하는 방식입니다. INSERT/DELETE 없이 이 한 행만 사용합니다.

| 컬럼 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| id | bigint | (고정값 1) | PK, 새 행 만들지 않음 |
| state | text | `'idle'` | 로봇 상태 (`idle`/`moving`/`stopped`/`camera_error`/`offline` — 웹 라벨 매핑 기준, `statusMap.js` 참고) |
| last_command | text | NULL | 마지막으로 실행한 command 문자열 |
| updated_at | timestamptz | now() | **heartbeat** |

### Heartbeat 규격

- **Raspberry Pi**: `updated_at`을 **5초마다** 갱신 (state/last_command도 함께 갱신)
- **Web**: 마지막 `updated_at`이 **15초 이상** 지나면 자동으로 OFFLINE 표시 (`web-redesign/src/lib/statusMap.js`의 `ROBOT_OFFLINE_THRESHOLD_MS = 15000`)

### RLS

- `anon_read_robot_status` — SELECT, 전체 허용
- **UPDATE 정책 없음** — anon key로 heartbeat 갱신 불가. Pi는 `service_role` key 사용 권장.

---

## lost_items

| 컬럼 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| id | bigint (identity) | 자동증가 | PK |
| image_url | text | NULL | Storage 공개 URL |
| item_type | text | NULL | `umbrella` / `bottle` / `backpack` |
| description | text | NULL | 선택 항목 (없으면 NULL 또는 빈 값 허용, 필수 아님) |
| confidence | numeric | NULL | **0~1 사이 숫자** (예: 0.91 = 웹에서 91%) |
| detected_at | timestamptz | now() | 탐지 시각 |
| location | text | NULL | 탐지 위치(구역명 등 자유 텍스트) |
| status | text | `'pending_analysis'` | 아래 표 참고 |
| created_at | timestamptz | now() | |

### item_type (분실물 클래스, 정확히 3종)

| DB 값 | 웹 표시 |
|---|---|
| `umbrella` | 우산 |
| `bottle` | 물병 |
| `backpack` | 가방(백팩) |

(웹 필터 UI에는 `handbag`, `suitcase` 옵션도 존재하지만 현재 AI 탐지 파이프라인의 확정 대상은 위 3종뿐입니다.)

### status (분실물 처리 상태)

| DB 값 | 웹 표시 | 누가 설정 |
|---|---|---|
| `pending_analysis` | AI 분석 중 | (초기값, 현재 웹은 이 값을 직접 쓰지 않음) |
| `new` | 확인 필요 | **AI/OpenCV 담당(조은수) — 탐지 확정 후 등록 시 초기값으로 사용** |
| `confirmed` | 보관 중 | 웹 관리자가 수동 변경 |
| `resolved` | 반환 완료 | 웹 관리자가 수동 변경 |
| `rejected` | 반려 | 웹 관리자가 수동 변경 |

AI 파이프라인이 `lost_items`를 INSERT할 때는 `status: 'new'`로 등록합니다.

### confidence 규칙

- 반드시 **0.0 ~ 1.0** 사이 숫자로 저장 (예: `0.91`)
- `91`처럼 퍼센트 정수로 저장하지 않습니다 — 웹이 `confidence * 100`으로 표시하기 때문에 정수로 넣으면 9100%처럼 표시됩니다.

### RLS

- `anon_read_lost_items` — SELECT, 전체 허용
- `anon_update_lost_item_status` — UPDATE, `status`가 위 5개 값 중 하나일 때만 허용 (웹의 상태 변경 기능이 사용)
- **AI 파이프라인의 INSERT는 anon 정책에 없습니다.** 새 분실물 등록(INSERT)은 `service_role` key로 수행하세요.

---

## Storage

| 항목 | 값 |
|---|---|
| bucket 이름 | `lost-item-photos` |
| public | `true` (공개 URL로 읽기 가능 — 웹에서 이미지 표시에 사용) |
| RLS(objects) | **정책 없음** — anon key로 파일 업로드(INSERT) 불가 |

사진 업로드는 `service_role` key로 수행하고, 업로드 후 받은 공개 URL을 `lost_items.image_url`에 저장하세요.

---

## 요약: 각 담당자가 지켜야 할 것

- **문자열 고정**: command 8종, item_type 3종, lost_items.status 5종, robot_status.state 값들은 여기 적힌 그대로 사용. 바꿔야 하면 코드로 바꾸지 말고 먼저 팀과 상의.
- **컬럼명 고정**: 새 컬럼이 필요하면 팀과 상의 후 결정. 혼자 ALTER TABLE 하지 않기.
- **쓰기 권한**: Pi/AI 쪽 백엔드 코드는 `service_role` key를 로컬 `.env`에만 저장해서 사용 (anon key로는 UPDATE/일부 INSERT가 막혀 있음).
