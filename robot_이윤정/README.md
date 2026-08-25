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

- `store.py` — Supabase 연동 레이어. `.env`에 `SUPABASE_ANON_KEY`가 있으면 실제 Supabase를, 없으면 로컬 JSON(`data/`)을 자동으로 사용합니다. (anon key만 사용 — service_role 아님. 강사 피드백 반영, `robot_commands`/`robot_status`/`safety_status`에 anon용 제한적 UPDATE RLS 정책 적용됨)
- `controller.py` — 명령 polling 루프, heartbeat(5초), patrol_start/patrol_stop 상태머신, 초음파 안전정지 자리(stub), 에러시 정지 우선 처리. `_move()`/`_grab_frame()`/`_check_obstacle()` 안쪽만 실물 하드웨어 코드로 교체하면 됩니다.
- `send_command.py` — 웹 없이 명령을 테스트로 넣어보는 CLI.
- `safety_monitor.py` — **별도 프로그램**. Arduino(FLAME 화염센서 + LM35DZ 온도센서 + 소음센서)를 USB 시리얼로 읽어서 `safety_status`/`patrol_events`에 반영. Arduino 도착 전까지는 `SERIAL_PORT` 미설정 시 자동으로 mock 값을 생성. `controller.py`와는 완전히 다른 하드웨어를 다루는 별개 프로세스라 따로 실행합니다.

실행:
```
cd robot_이윤정/mock_controller
pip install -r requirements.txt
cp .env.example .env   # SUPABASE_ANON_KEY 채워넣기

python controller.py        # 터미널 1 — 로봇 명령 처리
python safety_monitor.py    # 터미널 2 — 안전 센서 모니터링 (별개 프로세스)
```

command/컬럼명은 `../../docs/02_SUPABASE_DATA_CONTRACT.md` 기준을 그대로 따릅니다 (임의 변경 금지). `safety_status`/`patrol_events`는 아직 이 문서에 없는 새 테이블 — 스키마 제안은 `HARDWARE_REFERENCE.md` 참고, 백경률 쪽 테이블 생성 필요.
