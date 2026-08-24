# 이윤정 — Claude Code 작업 프롬프트 (그대로 복붙해서 사용)

아래 내용을 본인의 Raspberry Pi / Razbot 프로젝트 폴더를 VS Code로 열고, Claude Code에게 그대로 붙여넣으세요.

---

```
나는 LostPatrol이라는 팀 프로젝트의 Raspberry Pi(Razbot) 담당자야.
내 로봇 코드(모터 제어, 라인트레이싱, 초음파 센서, 카메라)를 Supabase와 연동해야 해.

먼저 아래 작업을 해줘:

1. 지금 이 폴더의 기존 코드 구조를 전체적으로 조사해줘.
   - 기존 모터 제어 코드가 어디 있는지
   - forward/backward/좌우회전을 어떻게 구현하고 있는지
   - 라인트레이싱 센서, 초음파 센서, 카메라 관련 코드가 있는지
   먼저 파악하고 나한테 요약해줘. 아직 아무것도 수정하지 마.

2. 조사 후에는 기존에 정상 동작하는 모터 제어 로직을 최대한 보존하면서,
   Supabase 연동 레이어만 추가해줘. 기존 코드를 불필요하게 전부 재작성하지 말고
   최소한의 수정으로 연결해줘.

Supabase 연동 규격은 다음과 같이 고정되어 있고, 절대 임의로 바꾸면 안 돼
(바꿔야 할 것 같으면 코드로 바꾸지 말고 나한테 먼저 물어봐):

[연결 정보]
- SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY는 .env 파일에서 읽어온다.
  (.env는 내가 직접 만들 것이고, 이 프롬프트에는 실제 키 값이 없다.
   .env를 .gitignore에 반드시 추가해줘. service_role key를 코드에 직접 쓰지 마.)
- service_role key를 쓰는 이유: robot_commands/robot_status 테이블에는
  현재 anon(publishable) key로 UPDATE할 수 있는 RLS 정책이 없기 때문이야.
  Pi는 신뢰된 디바이스니까 service_role key로 RLS를 우회해서 UPDATE한다.

[robot_commands 테이블] 컬럼: id, created_at, executed_at, command, status(기본값 pending)

command로 올 수 있는 값은 정확히 다음 8개뿐이야. 이 문자열들을 그대로 써야 해:
- forward = 직진
- backward = 후진
- left = 제자리 좌회전 (전진하면서 도는 게 아니라 그 자리에서 회전)
- right = 제자리 우회전 (마찬가지로 제자리 회전)
- stop = 즉시 정지
- capture = 카메라 촬영
- patrol_start = 라인트레이싱 기반 자동순찰 시작 (SLAM 아님, 바닥에 그려진 정해진 라인을 따라가는 방식)
- patrol_stop = 자동순찰 종료

동작 흐름:
1. status = 'pending' 인 행을 주기적으로(2~3초 간격) SELECT
2. command에 맞는 실제 로봇 동작 실행
3. 실행 끝나면 그 행을 status='done', executed_at=now()로 UPDATE
   (done은 이미 팀에서 쓰던 완료 상태 값이야. 실패 시 쓸 status 값은
    아직 팀에서 정해진 게 없으니 새로 만들지 말고 일단 done으로 두고
    실패 사실은 robot_status.state로 남겨줘.)
4. patrol_start/patrol_stop은 백그라운드 라인트레이싱 루프를 켜고 끄는
   토글 명령으로 처리해줘. 순찰 중에도 stop이나 다른 수동 명령이 오면
   즉시 그게 우선이야 (안전 정지가 항상 최우선).

[robot_status 테이블] 컬럼: id, state, last_command, updated_at
- id=1인 행 하나만 계속 UPDATE (새 행 만들지 마)
- 5초마다 updated_at을 반드시 갱신해줘 (heartbeat). 로봇이 명령 처리 중이라도
  heartbeat 타이머는 별도로 계속 돌아야 해.
- 웹은 updated_at이 15초 이상 갱신 안 되면 자동으로 OFFLINE으로 표시하니까,
  heartbeat가 끊기지 않게 신경써줘.
- state 값은 idle / moving / stopped / camera_error / offline 중에서 상황에 맞게 넣어줘.

[초음파 센서 안전 정지]
- 전방 거리를 계속 측정하다가, 일정 거리 이하로 장애물이 감지되면 즉시 정지시켜줘.
  회피 주행은 이번 범위가 아니고 "감지 → 안전 정지"까지만 구현하면 돼.
- 장애물 정지 거리(cm)는 팀에서 아직 확정 안 됐어. 코드에 숫자를 그냥 박지 말고
  OBSTACLE_STOP_DISTANCE_CM 같은 이름으로 설정 가능한 상수/설정값으로 빼두고
  주석에 "TBD - 팀 협의 후 확정"이라고 표시해줘.

[에러 처리 원칙]
- 어떤 예외/에러가 나든 로봇을 먼저 정지시키고 나서 로그를 남기거나 재시도해줘.
  ("오류 시 정지 우선")

[하지 말아야 할 것]
- command 문자열, 테이블/컬럼 이름을 임의로 바꾸지 마.
- 기존에 잘 동작하던 모터 제어 로직을 불필요하게 전부 새로 짜지 마.
- service_role key나 실제 비밀번호를 코드나 커밋에 직접 넣지 마.

구현이 끝나면 아래를 나한테 보고해줘:
1. 수정/추가한 파일 목록
2. robot_commands 폴링 및 robot_status heartbeat가 실제로 어떻게 동작하는지 요약
3. 내가 직접 테스트해볼 수 있는 방법 (Supabase Table Editor에서 어떤 걸 확인하면 되는지 포함)
```
