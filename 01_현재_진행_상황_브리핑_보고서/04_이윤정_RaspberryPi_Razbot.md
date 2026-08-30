# 04. 이윤정 담당 진행 상황 — Raspberry Pi / Razbot

실제 하드웨어(Yahboom Raspbot 계열) 도착 전까지, `robot_이윤정/mock_controller/`에 Mock Robot Controller를 구현해 Supabase 연동과 제어 로직을 먼저 검증하는 방식으로 진행하고 있습니다.

## ✅ 완료

- Mock Robot Controller 구현 (`controller.py`, `store.py`, `send_command.py`)
- Supabase `robot_commands` polling 구현 (1초 주기)
- Heartbeat 구현 (5초마다 `robot_status.updated_at` 갱신, 별도 스레드로 분리해 명령 처리 중에도 끊기지 않도록 처리)
- 순찰 상태머신 구현 (`patrol_start`/`patrol_stop` 토글, 수동 명령이 오면 순찰보다 항상 우선해서 즉시 정지)
- 안전정지 원칙 구현 (에러 발생 시 로봇을 먼저 정지시키고 로그를 남기는 "정지 우선" 원칙, 코드 전반에 반영)
- 웹캠 촬영 기능 구현 (`_capture()` — OpenCV로 프레임을 가져와 저장)
- anon(public) key 기반 Supabase 연동 성공, 기존 UPDATE RLS 오류 해결
- `forward`, `patrol_start`, `patrol_stop` 명령 왕복(웹 → Supabase → Pi 처리) 확인
- 관련 코드 팀 GitHub Repository에 commit/push 완료
- **Supabase Storage `lost-item-photos` anon RLS 정책 적용** (2026.08.25 11:43 KST): `storage.objects`에 `anon_insert_lost_item_photos` / `anon_read_lost_item_photos` / `anon_update_lost_item_photos` 3개 정책을 `bucket_id = 'lost-item-photos'` 범위로 한정해 추가. Storage 전체가 아니라 해당 버킷에 한해 anon key의 SELECT/INSERT/UPDATE만 허용하며, `pg_policies`에 실제 등록된 것을 확인했습니다. 기존 403 RLS 오류의 원인(정책 부재)은 이 조치로 해결되었습니다.

## 코드 개발 과정에서 발견 및 수정한 버그 3건

1. **한글 경로 cv2.imwrite 실패 문제**: 프로젝트 폴더 경로에 한글이 포함되어 있어 Windows에서 `cv2.imwrite`가 에러 없이 조용히 실패(False 반환)하는 문제를 발견. `cv2.imencode`로 메모리에 인코딩한 뒤 파이썬 파일 IO로 직접 저장하는 방식으로 수정.
2. **upsert 권한 문제**: `robot_status` 갱신에 `upsert()`를 사용하면 내부적으로 INSERT 권한까지 요구해(ON CONFLICT DO UPDATE) anon 권한(UPDATE만 허용)에서 오류가 발생. `update()`로 변경해 해결.
3. **Thread 내부 예외 전파 문제**: 순찰 스레드(`_patrol_loop`) 내부에서 발생한 예외가 메인 스레드의 try/except로 전파되지 않아 스레드가 조용히 죽는 문제를 발견. 해당 함수 자체를 try/except로 감싸 "에러 시 정지 우선" 원칙을 스레드 내부에서도 지키도록 수정.

웹사이트에서 `robot_status`가 실제 반영되어 로봇 상태가 ONLINE으로 정상 표시되는 것도 확인했습니다. 따라서 현재 **"로봇 소프트웨어 ↔ Supabase ↔ Web 기본 연결"**은 확인된 상태입니다.

## ✅ Storage 실제 업로드 재검증 완료 (2026.08.25)

`upload_capture()`로 테스트 이미지를 업로드하고 3중으로 검증했습니다:
1. `storage.objects` 목록(`list()`)에 실제 파일 존재 확인 (827 bytes)
2. 공개 URL로 직접 HTTP 요청 → `200 OK`, `Content-Type: image/jpeg` 확인
3. 파일 크기/내용 일치 확인

**결론: Storage 업로드 파이프라인은 실제 데이터로 완전히 검증되었습니다.** 조은수 담당자의 Vision 파이프라인도 동일한 방식(`upload_capture()` 패턴 또는 동일 버킷/정책)으로 안전하게 사용 가능합니다.

참고: anon 역할에는 DELETE 정책이 없어(INSERT/SELECT/UPDATE만 부여됨) 테스트 파일(`captures/verify_1787631493.jpg`, 827 bytes, 색상 테스트용 이미지)이 버킷에 남아있습니다 — 민감 정보 아니며, 정리하려면 대시보드 접근 권한이 있는 담당자가 수동 삭제하면 됩니다.

## ✅ Arduino 안전센서(Safety Monitoring) 실제 Supabase 연동 검증 완료 (2026.08.25)

`safety_monitor.py`(신규, `controller.py`와 별개 프로세스 — Arduino를 USB 시리얼로 읽어 `safety_status`/`patrol_events`에 반영) 구현 후, 백경률이 두 테이블과 anon RLS(safety_status: SELECT/UPDATE, patrol_events: SELECT/INSERT)를 생성해줘서 바로 실제 Supabase로 재검증했습니다.

- `safety_status`(id=1 고정 행) 실시간 갱신 확인
- 화재/소음 발생을 강제로 흉내내서 `patrol_events`에 `fire_detected` → `loud_sound` → `status_normal` 3건이 실제로 INSERT되는 것 확인 (상태가 바뀌는 순간에만 기록되는 로직도 함께 검증됨)
- 에러 0건

아직 Arduino 실물이 없어(주문 중) `safety_monitor.py`는 계속 mock 값으로 동작 중이며, 시리얼 포트(`SERIAL_PORT`)만 `.env`에 채우면 코드 수정 없이 실물 모드로 전환됩니다.

## ✅ 로봇 실물 도착 + 실제 모터 제어 연동 완료 (2026.08.26)

Razbot 실물 배송·조립 완료 후 당일 아래까지 전부 진행했습니다.

1. **SD카드 굽기 + 부팅**: 준비해뒀던 Yahboom 커스텀 이미지로 SD카드 굽고 부팅, "Raspbot" 자체 핫스팟(AP) 정상 진입 확인
2. **JupyterLab 터미널 접속**: `http://10.42.0.1:8888`(pw: `yahboom`)로 브라우저 접속 — SSH 계정 몰라도 여기서 터미널 사용 가능
3. **기본 실행 중이던 원격제어 앱 서버 정리**: `raspbot.py`(부모+자식 프로세스)가 기본으로 떠서 모터/카메라를 선점하고 있어 우리 코드와 충돌 가능 — `sudo kill`로 정리(단, 자동시작 등록돼 있어 재부팅마다 다시 뜸 → 매번 kill 필요, 완전 비활성화는 추후 과제)
4. **AP → STA(집 WiFi) 전환**: `raspi-config`(WLAN Country) → `nmcli --ask dev wifi connect`로 연결 성공. 재부팅하면 도로 AP로 돌아가는 문제 발견 → `connection.autoconnect-priority`로 집 WiFi 우선순위를 Raspbot AP보다 높여서 재부팅 후에도 유지되도록 해결. 현재 IP(DHCP, 유동): `192.168.0.67`
5. **로봇에서 팀 GitHub 저장소 clone**: `~/LostPatrol`에 clone, git 계정 설정(PAT 인증) 완료 — 이제 로봇에서 직접 pull/push 가능
6. **실제 모터 라이브러리(`YB_Pcb_Car.py`) 위치 확인 및 확보**: `~/Yahboom_project/Raspbot/raspbot/YB_Pcb_Car.py`에서 복사, 팀 저장소에 커밋
7. **실제 모터 동작 실물 테스트 성공**: `Car_Run()`(전진), `Car_Spin_Left()`(제자리 좌회전 — 실제로 제자리에서 도는 것 육안 확인) 둘 다 정상 동작
8. **`controller.py`의 `_move()`를 실제 모터 제어로 교체 완료**: `YB_Pcb_Car` import 성공 여부로 실물/mock 모드를 자동 분기하도록 구현 — 노트북(Windows)에서는 여전히 mock으로 안전하게 테스트 가능하고, 로봇(라즈베리파이)에서는 실제로 움직임. `forward/backward`는 `Car_Run`/`Car_Back`, **`left/right`(제자리 회전)는 `Car_Spin_Left`/`Car_Spin_Right`**로 매핑(`Car_Left`/`Car_Right`는 곡선주행이라 계약과 안 맞아 사용 안 함)

## ✅ 웹→Supabase→실물 로봇 엔드투엔드 + 실제 카메라 연동 완료 (2026.08.26)

같은 날 이어서 아래까지 완료했습니다.

- **웹 Forward 버튼 → 실물 로봇 이동 엔드투엔드 확인**: 배포된 웹사이트에서 Forward 클릭 → 실제로 로봇이 움직이는 것 확인 (`03_INTEGRATION_TEST_CHECKLIST.md` 1번 항목 통과)
- **회전 시간 튜닝**: `left`/`right`가 1.5초 기준이라 실물에서 거의 한 바퀴 넘게 돌던 문제 발견 → 제자리회전 전용 `SPIN_DURATION_SEC(0.3초)`로 분리해 조금씩만 돌도록 수정
- **Razbot 카메라(CSI) 실제 연동**: `cv2.VideoCapture()`로는 프레임을 못 읽는 것 확인(CSI 카메라라 libcamera 스택 필요, `rp1-cfe`/`pispbe` 드라이버). `picamera2`는 시스템에 있으나 numpy 바이너리 호환성 문제로 깨져있어, 대신 `rpicam-still` 커맨드라인 도구를 서브프로세스로 호출해 JPEG를 받는 방식으로 우회 구현. `_grab_frame()`이 `rpicam-still` 존재 여부로 실물/웹캠 자동 분기
- **촬영→저장→업로드 엔드투엔드 실물 검증**: 실제 카메라로 촬영(205KB 진짜 사진) → 로컬 저장 → `upload_capture()`로 Supabase Storage 업로드 → 공개 URL로 실제 이미지 확인까지 전부 성공
- **배터리 이슈 대응**: 리튬 배터리 방전으로 모터 테스트 불가 시, 라즈베리파이 USB-C 단독 전원으로 부팅해 카메라/소프트웨어 테스트는 계속 진행 가능함을 확인(모터는 배터리 별도 전원이라 USB-C만으로는 동작 안 함 — 실물로 재확인)

## ✅ Vision 파이프라인 실물 연동 + 엔드투엔드 검증 완료 (2026.08.26)

조은수의 학습 모델(`best.pt`, `eunsoo0229/LostPatrolAI`)이 아직 팀 저장소의 Supabase 연동 코드와 연결되어 있지 않아, 본인 담당은 아니지만 팀 진행을 위해 연결 스크립트를 직접 작성했습니다(`vision_조은수/detect_and_register.py`, 조은수가 자유롭게 수정 가능한 초안으로 커밋).

- **클래스명 매핑**: 조은수 모델의 `backpack`/`umbrella`/`waterbottle` → 팀 Data Contract의 `backpack`/`umbrella`/`bottle`로 변환하는 `CLASS_NAME_MAP` 추가
- **연속 검출 디바운스**: 체크리스트 요구사항("2~3회 연속 검출 확인 후")에 맞춰 동일 클래스가 2회 연속 검출되어야 등록되도록 구현
- **실물 카메라 엔드투엔드 검증 성공**: 실제 Razbot 카메라로 backpack 촬영 → 연속 2회 감지 → Storage 업로드 → `lost_items` INSERT까지 전부 실물로 확인 (id=4)
- **⚠️ 모델 분류 정확도 이슈 발견**: 실물 카메라(로우엔드 CSI, 이전에는 색보정도 안 된 상태)로 찍은 사진 기준 모델 정확도가 낮음
  - 스테인리스 텀블러: threshold를 0.05까지 낮춰도 전혀 미검출
  - 투명 페트병(생수병): `umbrella`로 오분류 (conf 0.72~0.75, id=6)
  - 사진 자체(초점/조명/프레이밍)는 정상 확인됨 — 카메라 하드웨어 문제가 아니라 **학습 데이터가 실제 Pi 카메라로 찍은 사진과 다르기 때문으로 판단**(조은수는 폰카메라로 학습). 조은수에게 재학습 피드백 전달 필요.
  - `lost_items.id=6`은 anon key로 삭제 불가 — 백경률에게 Dashboard 삭제 요청 필요

## ✅ 초음파/라인트레이싱 센서 실물 검증 (2026.08.26)

- **초음파 센서**: `_measure_distance_cm()` 실물로 5회 반복 측정, 장애물과의 거리에 따라 값이 정확히 변화하는 것 확인 (근접 시 거리값 감소). GPIO 배선/코드 정상 동작.
- **라인트레이싱 센서(4채널)**: 처음엔 4채널 전부 0으로 고정되는 문제 발생. 디버깅 과정:
  1. `GPIO busy` 에러 → 원인은 이전에 떠있던 `controller.py` 프로세스가 해당 GPIO 핀을 이미 점유 중이었던 것(`ps -ef`가 터미널 폭 때문에 `controller.py`를 `controller`로 잘라서 처음엔 못 찾음). 해당 프로세스 kill 후 해결.
  2. GPIO 자체는 초기화됐지만 4채널 전부 흰바탕/검은선 구분 없이 0 고정 → 센서 모듈이 거꾸로 장착되어 있었음(본인 확인 후 재장착)
  3. 재장착 후에도 여전히 반응 없음, 모듈 자체 개별 LED도 무반응 → 감도(트리머) 캘리브레이션 문제로 진단
  4. 트리머로 감도 조절 후 최종적으로 흰바탕(1)/검은선(0)에 따라 4채널 값이 정확히 반전되는 것 확인 완료
- 순찰 상태머신(`_patrol_loop()`)에 필요한 센서 입력 두 종류(초음파/라인트레이싱)는 이제 하드웨어 레벨에서 모두 검증됨.

## ✅ PATROL START/STOP + 장애물 안전정지 웹 통합 테스트 완료 (2026.08.26)

- 웹에서 **PATROL START** 클릭 → 실제로 라인을 따라 주행, 이탈 시 스스로 좌/우 보정하는 것 확인
- 순찰 중 20cm 이내 장애물 감지 → 자동으로 **안전 정지**되는 것 확인 (`_check_obstacle()` → `_patrol_active.clear()` 경로 실물로 검증)
- 장애물 없는 상태로 재시도 → 웹 **PATROL STOP** 클릭 → 정상 종료 확인
- 이로써 `03_INTEGRATION_TEST_CHECKLIST.md` 1~7, 9~11번 전부 실물로 검증 완료. 남은 건 8번(heartbeat 끊김→OFFLINE 표시, 15초) 뿐.

## ✅ 아두이노 안전센서(FLAME/LM35DZ/소음) 실물 시리얼 연동 완료 (2026.08.26)

`safety_monitor.py`가 mock이 아니라 실제 아두이노 시리얼 데이터를 읽어서 Supabase(`safety_status`)에 반영하는 것까지 확인. 스케치(`robot_이윤정/arduino_safety_monitor/arduino_safety_monitor.ino`)를 새로 작성하고, 배선 확정 전까지 여러 단계로 디버깅함:

1. FLAME은 비교기 내장 모듈이 아니라 포토트랜지스터+저항 직접 구성 회로라 `digitalRead()`가 아니라 `analogRead()` + 임계값(실측으로 5 확정) 방식으로 변경
2. 소음/LM35DZ 핀이 실제 배선과 반대로 코드에 들어가 있어서 온도가 항상 ADC 최댓값(499.5도)으로 나오던 문제 → 실제 배선(A0=FLAME, A1=LM35DZ, A2=소음)에 맞춰 수정
3. 소음센서는 트리머로 감도 캘리브레이션(평소 0, 큰 소리에만 1)
4. LM35DZ 값이 5.9~73.7도로 튀는 노이즈 → 여러 번 읽어 평균내는 방식으로 안정화
5. Pi 연결 초반 계속 `\x00` 널 바이트만 읽히는 문제 → ModemManager(포트 자동 간섭 서비스) 비활성화 + 시리얼 오픈 직후 대기/버퍼 flush 추가로 시도했으나 계속 재현 → 최종 원인은 **USB 케이블 접촉 불량**이었음(케이블 흔들자 TX LED가 바로 정상적으로 깜빡이기 시작)
6. 라이터로 FLAME 반응 테스트 → Supabase `safety_status`에 실시간으로 `fire_severity=danger`, `temperature_c=170.4` 등 실제 값 반영되는 것을 직접 쿼리로 재확인

## ✅ 로봇 얼굴 표시(LCD1602 + OLED/RoboEyes, ESP32) 추가 (2026.08.27)

계약에는 없는 부가 기능이지만, 안전센서 상태를 시각적으로도 표시하고 싶어서 진행. 최종적으로는 하드웨어 제약 때문에 **우노(센서+LCD) + 별도 ESP32(OLED 얼굴 애니메이션)** 두 보드로 나누는 구조로 정착했습니다.

1. 처음엔 LCD1602(I2C, 0x27)에 텍스트로 눈 깜빡임(`^_^`/`-_-`) 표정을 넣음 → 반응 요청으로 `createChar()` 커스텀 픽셀 눈(뜸/반감김/감음)과 좌우 곁눈질(커서 위치 이동)까지 구현
2. RoboEyes(FluxGarage, OLED 전용 애니메이션 눈 라이브러리)로 업그레이드하려고 실제 장착된 디스플레이를 확인해보니 LCD1602가 아니라 OLED(SSD1306, 0x3C)였음 — Adafruit GFX/SSD1306 라이브러리로 그래픽 얼굴 재구현
3. 이후 "LCD는 텍스트용, OLED는 RoboEyes 애니메이션용으로 같이 쓰자"는 요청으로 둘 다 우노 한 대에 병렬 연결(I2C 버스 공유, 주소만 다름) 시도
4. `display.begin()`이 계속 실패 → 남은 메모리를 출력해서 확인해보니 1058바이트뿐 → OLED 프레임버퍼(128x64=1024바이트)만으로도 우노의 총 RAM(2KB)이 거의 소진되는 게 원인으로 확정
5. 여분으로 있던 **ESP32-C3로 OLED+RoboEyes를 통째로 분리**해서 해결 — 우노는 원래 하던 센서+LCD만 담당하고, flame/sound 판정 결과를 디지털 신호 2개(D8/D9 → ESP32 GPIO4/5)로 그대로 넘겨줌(WiFi나 라즈베리파이 경유 없이 직결). 우노 쪽 새 스케치는 `robot_이윤정/arduino_safety_monitor/arduino_safety_monitor.ino`, ESP32 쪽은 `robot_이윤정/esp32_face/esp32_face.ino`
6. ESP32 쪽 디버깅: RoboEyes는 템플릿 클래스라 실제 `Adafruit_SSD1306` 객체를 만들어 참조로 넘겨야 함(클래스명도 `roboEyes`가 아니라 `RoboEyes`), `Wire.begin(SDA, SCL)`으로 커스텀 I2C 핀 지정, 실물 테스트로 OLED 정상 인식(`display.begin()` 성공) 및 애니메이션(자동 깜빡임+시선 이동) 확인 완료
7. ESP32는 컴퓨터 USB 연결이 끊기면 당연히 꺼짐(전원 문제일 뿐, 정상) — 라즈베리파이 USB 포트에 꽂으면 그대로 켜져서 동작함

## ✅ 안전센서 하드웨어 안정화 + GPIO 자동시작 문제 영구 해결 (2026.08.29)

- **LM35DZ 온도센서 물리적 파손 발견**: 배선/코드/캘리브레이션을 순서대로 배제하며 추적하던 5.9~130도 오락가락 문제의 진짜 원인이 센서 다리 자체의 물리적 파손이었음을 확인. 예비 부품이 없어 온도 기능 자체를 제거(프로토콜 호환을 위해 `temp_c:0.0`은 계속 전송), 화재 판정은 FLAME 센서만으로 계속함
- 화재 감지 시 켜지는 LED(D7), 소음 감지 시 켜지는 LED(D13) 추가, LCD에 화재 시 긴급 경보 문구("!!! FIRE! !!! / Send Help Now!") 추가
- ESP32 로봇 얼굴에 화재/소음 감지 시 놀란 표정(ANGRY + 흔들림 애니메이션), 평소 대기 중 가끔 웃는 표정 추가
- **`raspbot.pyc` GPIO 선점 문제 영구 해결**: 재부팅마다 자동으로 다시 떠서 그때그때 수동 kill로 대응해오던 문제의 근본 원인이 `/etc/rc.local`에 등록된 자동 실행 줄임을 확인, 해당 줄을 주석 처리해서 재발하지 않도록 조치 — 남은 과제였던 항목 완료

## ✅ 소음 감지 방식 재설계 — 세 번의 시행착오 끝에 안정화 (2026.08.30)

D0(비교기)+트리머 방식은 "전혀 반응 없음"과 "항상 반응함" 사이의 유효 구간이 너무 좁아 실사용이 어려웠음. FLAME과 같은 방식(아날로그+코드 임계값)으로 바꿨더니 이번엔 오디오 파형을 평균내면 상쇄되어 항상 중간값(~490)에 고정되는 새로운 문제가 발생 — 짧은 시간(50ms) 동안의 진폭(최댓값-최솟값)을 측정하는 방식으로 재설계해 최종 안정화함.

## ✅ 자동순찰 조향/장애물 로직 개선 (2026.08.30)

- 라인 이탈 시 제자리 회전(Car_Spin)을 쓰던 걸 전진 방향을 유지한 채 속도차만 주는 커브(Control_Car)로 바꿔, "바깥쪽 센서가 반응했는데 전진을 안 하는" 문제 해결
- 라인을 완전히 놓쳤을 때 바로 정지하는 대신, 직전 진행 방향을 기억해뒀다가 그 방향부터 먼저 재탐색하도록 구현해 직각 코너 대응력 향상, 못 찾으면 좌우 번갈아 검색으로 전환
- 순찰 속도(80→60)와 조향 세기 값들을 실물 테스트로 재조정 (너무 낮추면 모터가 정지 마찰을 못 이겨 안 움직이는 것도 확인)

## ✅ 장애물 감지 → 분실물 자동 등록 엔드투엔드 파이프라인 완성 (2026.08.30)

- 장애물 감지 시 정지 → 촬영 프레이밍 확보를 위한 소폭 후진 → 연속 촬영(3장, `detect_and_register.py`의 "연속 2회 감지" 조건 충족용) → 자동 분실물 등록까지 실물로 검증 완료
- **촬영 화질 이슈 발견·해결**: 실시간 스트리밍 서버(`stream_server.py`)가 계속 켜져 있으면 저해상도(640x480) 압축 프레임이 재사용되어 YOLO 인식률이 떨어지는 것을 확인. 스트리밍 서버가 고해상도 촬영 요청을 받으면 스스로 스트리밍을 잠깐 멈추고 고해상도(1296x972)로 찍은 뒤 재개하도록 조율하는 구조(`/hq_snapshot.jpg` 엔드포인트)로 화질과 카메라 리소스 충돌 문제를 동시에 해결
- 같은 물건이 짧은 시간 안에 중복 등록되는 문제를 발견해, 같은 종류는 일정 시간(기본 5분) 안 재등록하지 않는 쿨다운 로직 추가

## ✅ 웹 프론트엔드 버그 수정 (2026.08.30 — 백경률 담당 영역이지만 사용성 문제 발견해 직접 수정)

- 순찰 시작/정지 버튼이 페이지 로컬 상태로만 관리되어, 순찰 중 다른 페이지로 이동했다 돌아오면 STOP 버튼이 비활성화되는 문제 → 실제 로봇 상태(`last_command`) 기준으로 판단하도록 수정
- 카메라 스트림 URL이 설정만 돼있으면 서버가 꺼져있어도 항상 "ONLINE"으로 표시되던 문제 → 실제 이미지 로드 성공/실패를 감지해 정확히 표시하도록 수정
- 안전상태가 웹에 반영되기까지 최대 7~9초 지연되던 것을 발견 → 시리얼 버퍼 누적 지연 제거 + 폴링 주기 단축(Pi 2s→1s, 웹 5s→2s)

## ✅ 시연 영상 5장면 촬영 완료 (2026.08.29~30)

① 웹 버튼 → 실제 로봇 이동 ② 자동순찰 ③ 장애물 감지 → 자동정지 ④ 분실물 감지 및 웹사이트 등록 확인 ⑤ 화재 감지 → 웹 경고 + 표정 변화, 이상 소음 감지 웹 표시. 시연용 가짜 동작 코드는 절대 커밋하지 않는다는 원칙을 지키면서, 실제 라인트레이싱·실물 센서 기반으로만 촬영함.

## ⬜ 남은 과제

- 초음파 센서 배선/신호 재점검 (거리값이 간헐적으로 `None`으로 나오는 경우가 있음 — 장애물 감지 로직 자체는 코드로 완성돼있어 센서 신호만 안정화하면 됨)
- 온도센서(LM35DZ) 교체 또는 기능 완전 대체 여부 팀 협의
- 백경률에게 `lost_items` 테스트용 중복 항목(id=6, 11, 13 등) 삭제 요청

## ⚠️ 팀 내 확인 필요

- 초음파 안전정지 거리(`OBSTACLE_STOP_DISTANCE_CM = 20`)는 코드상 자리표시자 값이며, 초음파 센서 신호가 안정화되면 실측 기반으로 팀 협의해 확정해야 합니다.
