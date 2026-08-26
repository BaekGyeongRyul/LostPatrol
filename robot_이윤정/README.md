# robot_이윤정/

이윤정 담당 — Raspberry Pi / Razbot / Arduino 안전센서 / ESP32 로봇 얼굴 코드 위치.

담당 범위: Raspberry Pi, Razbot(모터/카메라/초음파/라인트레이싱), Arduino 안전센서, Supabase Robot Command 처리, Heartbeat.

> **2026.08.26~27 기준: 실물 하드웨어 전부 도착 + 통합 완료.** 아래는 "mock 도착 전 임시 구현"이 아니라 실제 로봇으로 동작 확인까지 끝난 현재 상태입니다. 자세한 진행 이력은 [`../01_현재_진행_상황_브리핑_보고서/04_이윤정_RaspberryPi_Razbot.md`](../01_현재_진행_상황_브리핑_보고서/04_이윤정_RaspberryPi_Razbot.md) 참고.

연동 규격 문서:
- `../docs/02_SUPABASE_DATA_CONTRACT.md` — command/컬럼명 등 팀 계약, 임의 변경 금지
- `../docs/YOONJEONG_RAZBOT_GUIDE.md`, `../docs/YOONJEONG_CLAUDE_CODE_PROMPT.md`
- `HARDWARE_REFERENCE.md` — 하드웨어 도착 전 조사한 배선/API 참고 자료(모터 라이브러리, WiFi 전환 등)

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `mock_controller/` | 실제 로봇 실행 코드 전부(이름은 "mock"이지만 실물에서도 그대로 씀 — 하드웨어 없으면 자동으로 mock으로 동작하는 구조라 이름을 유지) |
| `arduino_safety_monitor/` | 아두이노 우노 스케치(안전센서 3종 + LCD1602 텍스트 상태 표시) |
| `arduino_safety_monitor/i2c_scanner/` | I2C 장치 주소 확인용 스캐너 스케치 |
| `esp32_face/` | ESP32-C3 스케치(OLED + RoboEyes 로봇 얼굴 애니메이션, 우노와 신호선 2개로 직결) |

## `mock_controller/` 스크립트별 설명

라즈베리파이에서 **독립된 여러 프로세스**로 각각 따로 실행합니다 (터미널 탭을 나눠서).

| 파일 | 역할 | 실행 |
|---|---|---|
| `store.py` | Supabase 연동 레이어(import해서 씀, 직접 실행 안 함). `.env`의 `SUPABASE_ANON_KEY` 유무로 실제 Supabase/로컬 JSON을 자동 전환 | — |
| `controller.py` | **메인 로봇 제어**: 명령 polling(1초), 모터(`YB_Pcb_Car`), 카메라 촬영, 초음파/라인트레이싱 기반 자동순찰, heartbeat(5초) | `python3 controller.py` |
| `safety_monitor.py` | 아두이노(FLAME+LM35DZ+소음)를 USB 시리얼로 읽어서 `safety_status`/`patrol_events`에 반영 | `python3 safety_monitor.py` |
| `motion_monitor.py` | 카메라로 사람/움직임 감지 → `safety_status.motion_severity`/`person_detected` 반영(원래 조은수 담당으로 설계된 항목, 미구현 상태라 이윤정이 작성) | `python3 motion_monitor.py` |
| `stream_server.py` | `rpicam-vid` 기반 실시간 MJPEG 스트리밍(`http://<Pi IP>:8090/stream.mjpg`), 웹 Live Camera에 연결됨 | `python3 stream_server.py` |
| `send_command.py` | 웹 없이 명령을 테스트로 넣어보는 CLI | `python3 send_command.py <command>` |
| `YB_Pcb_Car.py` | Yahboom 공식 모터 드라이버 라이브러리(Pi에서 그대로 복사) | — |

실행 준비:
```bash
cd robot_이윤정/mock_controller
pip install -r requirements.txt
cp .env.example .env   # SUPABASE_ANON_KEY 채워넣기 (anon key만 사용, service_role 아님)
```

동시에 켜두면 좋은 조합(전체 기능):
```bash
python3 controller.py        # 필수 — 모터/카메라/순찰
python3 safety_monitor.py    # 아두이노 안전센서
python3 motion_monitor.py    # 카메라 기반 움직임/사람 감지
python3 stream_server.py     # 실시간 화면 송출 (켜두면 controller.py의 capture 명령이 자동으로 이 스트림의 프레임을 재사용해서 카메라 충돌 없음)
```

## 실물 하드웨어 현황 (2026.08.26~27 검증 완료)

- **모터**: `YB_Pcb_Car` 실제 제어, `forward/backward`=`Car_Run/Car_Back`, `left/right`(제자리 회전)=`Car_Spin_Left/Car_Spin_Right`
- **카메라**: CSI 카메라, `rpicam-still`/`rpicam-vid` 서브프로세스 방식(`cv2.VideoCapture()` 안 됨). `--rotation 180`(거꾸로 장착됨), `--awb daylight`(기본 auto는 초록빛 틀어짐) 필수
- **초음파**: HC-SR04류, BOARD 18(Echo)/16(Trig)
- **라인트레이싱**: 4채널, BOARD 13/15/11/7 — 실물 장착 시 트리머로 감도 캘리브레이션 필요할 수 있음
- **자동순찰**: 웹 PATROL START/STOP → 실제 라인트레이싱 주행 + 장애물 안전정지까지 실물 확인 완료
- **아두이노 안전센서**: FLAME(포토트랜지스터+저항, `analogRead()`+임계값 5), 소음(비교기 모듈, 트리머 캘리브레이션), LM35DZ(여러 번 읽어 평균) — 배선/코드 이력은 `arduino_safety_monitor/arduino_safety_monitor.ino` 상단 주석 참고
- **로봇 얼굴**: 우노 RAM 부족(2KB)으로 LCD+OLED+RoboEyes를 한 보드에 못 올려서, OLED+RoboEyes만 별도 ESP32-C3로 분리(`esp32_face/`). 우노↔ESP32는 디지털 신호선 2개(D8/D9)+공통GND로 직결, WiFi 불필요
- **움직임/사람 감지**: OpenCV Haar cascade(`haarcascade_frontalface_default.xml`, Yahboom 기본 제공 파일 재사용) — `person_detected`는 실물 확인됨, `motion_severity` 임계값은 아직 튜닝 중(TBD)

## 알려진 이슈 / TBD

- `motion_monitor.py`의 `MOTION_WARNING_PCT`/`MOTION_DANGER_PCT`는 자리표시자 — 실물 테스트로 계속 조정 필요
- `OBSTACLE_STOP_DISTANCE_CM`(초음파 안전정지 거리, 현재 20cm)은 팀 협의 전 자리표시자
- `raspbot.py`(Yahboom 기본 앱)가 매 부팅마다 자동 시작되어 GPIO/I2C/카메라를 점유함 — 매번 `sudo kill`로 수동 종료 중, 영구 비활성화 필요
- `stream_server.py`의 스트리밍 주소는 라즈베리파이의 로컬 네트워크 IP라서 Pi IP가 바뀌면 웹 쪽(`web_백경률/src/data/mockPatrolData.js`의 `cameraStreamUrl`)도 다시 맞춰야 함
