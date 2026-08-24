# Raspberry Pi / Razbot 연동 가이드 (담당: 이윤정)

담당 범위: Raspberry Pi, Razbot 모터 제어, 라인트레이싱, 초음파 센서, 카메라 연동, Supabase Robot Command 처리, Heartbeat.

먼저 `02_SUPABASE_DATA_CONTRACT.md`를 읽고 오세요. 이 문서는 그 내용을 실제 Pi 코드로 어떻게 옮길지에 대한 실행 가이드입니다.

## 0. 준비물

- Supabase 프로젝트 URL: `https://uityxtduglbshnvkstvx.supabase.co`
- **`service_role` key** (Supabase 대시보드 > Project Settings > API에서 본인이 직접 확인 — 이 문서나 웹 코드 어디에도 실제 값은 적혀 있지 않습니다)
- 이유: `robot_commands`/`robot_status`에는 현재 anon(publishable) key로 UPDATE할 수 있는 RLS 정책이 없습니다. Pi는 신뢰된 디바이스이므로 `service_role` key를 로컬 `.env`에만 저장해서 사용하세요. (`04_ENV_AND_SECURITY_GUIDE.md` 참고)

```
# Pi 쪽 .env 예시
SUPABASE_URL=https://uityxtduglbshnvkstvx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<본인이 대시보드에서 확인한 값>
```

Python이면 `supabase-py`(`pip install supabase`) 또는 `requests`로 REST(`/rest/v1/...`)를 직접 호출해도 됩니다.

## 1. 수동 조작 명령 규격 (절대 변경 금지)

| command | 의미 |
|---|---|
| `forward` | 직진 |
| `backward` | 후진 |
| `left` | **제자리 좌회전** — 좌우 바퀴를 반대 방향으로 굴려서 그 자리에서 도는 것. 자동차처럼 앞으로 나아가며 도는 것이 아닙니다. |
| `right` | **제자리 우회전** — 위와 동일하되 반대 방향 |
| `stop` | 즉시 정지 (모든 모터 출력 0) |
| `capture` | 카메라 촬영 트리거 (이 이벤트 자체는 로봇 이동과 무관, 필요 시 AI 파이프라인과 연계) |
| `patrol_start` | 라인트레이싱 자동순찰 시작 |
| `patrol_stop` | 자동순찰 종료 (즉시 정지 + 순찰 루프 종료) |

## 2. robot_commands 데이터 흐름

1. 2~3초 간격 정도로 폴링:
   ```sql
   select * from robot_commands where status = 'pending' order by created_at asc;
   ```
2. 각 pending 행에 대해 `command` 문자열로 분기해서 실제 모터/센서 동작 실행
3. 실행이 끝나면 **반드시 해당 행을 업데이트**해서 같은 명령을 중복 실행하지 않게 합니다:
   ```sql
   update robot_commands set status = 'done', executed_at = now() where id = <해당 id>;
   ```
   - `done`은 이미 웹 쪽 mock 코드에서 쓰던 값과 동일하게 맞춘 컨벤션입니다. 실패 시 어떤 값을 쓸지는 아직 팀 협의가 안 됐으니 임의로 새 값을 만들지 말고, 우선 `done`으로 두고 실패 내용은 `robot_status.state`(예: `camera_error`)로 남기세요.
4. 이미 처리한 명령(`status != 'pending'`)은 다시 실행하지 않도록 주의하세요.

의사코드:

```python
while True:
    pending = supabase.table("robot_commands").select("*").eq("status", "pending").order("created_at").execute()
    for row in pending.data:
        handle_command(row["command"])  # forward/backward/left/right/stop/capture/patrol_start/patrol_stop
        supabase.table("robot_commands").update({
            "status": "done",
            "executed_at": datetime.utcnow().isoformat(),
        }).eq("id", row["id"]).execute()
    time.sleep(2)
```

`patrol_start`/`patrol_stop`은 즉시 완료 처리하는 "토글성" 명령입니다 — 순찰 자체는 별도의 백그라운드 루프(라인트레이싱 상태 머신)로 계속 돌리고, 이 명령은 그 루프를 켜고 끄는 스위치 역할만 합니다.

`stop` 명령이나 새로운 수동 명령이 들어오면 자동순찰 루프보다 우선해서 즉시 정지해야 합니다. (안전 정지가 항상 최우선)

## 3. robot_status — heartbeat

단일 행(`id = 1`)을 계속 UPDATE합니다. 새 행을 만들지 마세요.

```python
def send_heartbeat(state, last_command):
    supabase.table("robot_status").update({
        "state": state,             # idle / moving / stopped / camera_error / offline 중 하나
        "last_command": last_command,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", 1).execute()
```

- **5초마다** 반드시 호출 (별도 스레드/타이머로 구현 권장 — 로봇이 명령을 처리하느라 바쁠 때도 heartbeat는 끊기면 안 됩니다)
- 웹은 마지막 `updated_at`이 **15초** 이상 지나면 자동으로 OFFLINE 표시합니다. 5초 heartbeat가 2~3번 연속 실패하면 웹에서 바로 티가 납니다.

## 4. 라인트레이싱 자동순찰 (patrol_start / patrol_stop)

- 방식: **SLAM/자율 경로 생성이 아니라, 바닥에 그려진 정해진 Line을 반복 추적하는 Line Tracking 방식**입니다.
- `patrol_start` 수신 시: 라인트레이싱 센서 값을 읽어 정해진 라인을 따라가는 제어 루프 시작, `robot_status.state`를 `moving` 등으로 갱신
- `patrol_stop` 수신 시: 루프 종료 + 즉시 정지, `state`를 `idle`/`stopped` 등으로 갱신
- 순찰 중에도 웹에서 `stop`이 오면 즉시 정지해야 합니다 (수동 개입이 항상 우선)

## 5. 초음파 센서 안전 정지

- 초음파 센서로 전방 거리를 계속 측정
- **일정 거리 이하로 장애물이 감지되면 즉시 정지**시킵니다 (회피 주행까지는 이번 범위에 포함되지 않음 — 감지 → 안전 정지까지만 구현)
- **장애물 정지 거리(cm)는 아직 팀에서 확정하지 않았습니다.** 코드에 `20` 같은 숫자를 그냥 박아넣지 말고, 아래처럼 **설정 가능한 상수/설정값(threshold)**로 빼두고 주석에 `TBD - 팀 협의 후 확정`이라고 표시하세요.

```python
# TBD - 팀 협의 후 확정. 우선 임시값으로 두되, 반드시 설정에서 바꿀 수 있게 유지.
OBSTACLE_STOP_DISTANCE_CM = 20  # <- placeholder, 확정값 아님
```

## 6. Secret / 오류 처리 원칙

- `SUPABASE_SERVICE_ROLE_KEY`는 코드에 직접 쓰지 않고 `.env` + `os.environ`(또는 `python-dotenv`)로 불러옵니다. `.env`는 Git에 커밋하지 않습니다.
- 예외/오류 발생 시에는 **항상 로봇을 먼저 정지시키고** 그 다음에 로그를 남기거나 재시도합니다 ("오류 시 정지 우선").

## 7. Web과 연결 테스트 순서

1. Pi 스크립트 실행 → `robot_status.updated_at`이 5초마다 갱신되는지 Supabase Table Editor에서 직접 확인
2. 웹(`FINAL_WEB/dist-share/index.html` 또는 `web-redesign` dev 서버)에서 로봇 상태가 ONLINE으로 뜨는지 확인
3. 웹에서 forward/backward/left/right/stop/capture 각각 클릭 → Pi 로그와 실제 동작 확인 → `robot_commands.status`가 `done`으로 바뀌는지 확인
4. PATROL START/STOP 클릭 → 라인트레이싱 시작/종료 확인
5. 장애물을 로봇 앞에 두고 자동순찰 중 안전 정지되는지 확인
6. Pi를 강제 종료하고 15초 후 웹이 OFFLINE으로 바뀌는지 확인

자세한 체크리스트는 `03_INTEGRATION_TEST_CHECKLIST.md`를 사용하세요. 바로 붙여넣어 쓸 수 있는 작업 프롬프트는 `YOONJEONG_CLAUDE_CODE_PROMPT.md`에 있습니다.
