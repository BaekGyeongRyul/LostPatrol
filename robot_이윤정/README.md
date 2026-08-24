# robot_이윤정/

이윤정 Raspberry Pi / Razbot 코드 위치

담당 범위: Raspberry Pi, Razbot, Motor 제어, Line Tracking, Ultrasonic Sensor, Camera 연동, Supabase Robot Command 처리, Heartbeat.

연동 규격과 구현 가이드는 다음 문서를 참고하세요.

- `../docs/02_SUPABASE_DATA_CONTRACT.md`
- `../docs/YOONJEONG_RAZBOT_GUIDE.md`
- `../docs/YOONJEONG_CLAUDE_CODE_PROMPT.md`

실제 Raspberry Pi/Razbot 소스 코드가 준비되면 이 폴더 아래에 추가해주세요.

## 현재 상태: mock_controller (로봇 도착 전 임시 구현)

`mock_controller/`에 실물 로봇 도착 전까지 쓸 스텁 구현이 있습니다.

- `store.py` — Supabase 연동 레이어. `.env`에 `SUPABASE_SERVICE_ROLE_KEY`가 있으면 실제 Supabase를, 없으면 로컬 JSON(`data/`)을 자동으로 사용합니다.
- `controller.py` — 명령 polling 루프, heartbeat(5초), patrol_start/patrol_stop 상태머신, 초음파 안전정지 자리(stub), 에러시 정지 우선 처리. `_move()`/`_grab_frame()`/`_check_obstacle()` 안쪽만 실물 하드웨어 코드로 교체하면 됩니다.
- `send_command.py` — 웹 없이 명령을 테스트로 넣어보는 CLI.

실행:
```
cd robot_이윤정/mock_controller
pip install -r requirements.txt
cp .env.example .env   # SUPABASE_SERVICE_ROLE_KEY 채워넣기
python controller.py
```

command/컬럼명은 `../../docs/02_SUPABASE_DATA_CONTRACT.md` 기준을 그대로 따릅니다 (임의 변경 금지).
