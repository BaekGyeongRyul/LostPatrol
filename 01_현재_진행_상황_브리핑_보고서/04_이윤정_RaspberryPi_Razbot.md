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

## ⬜ 남은 과제

- Arduino 실물 도착 후 시리얼 연동 + 온도/소음 임계값 캘리브레이션
- 실제 라인트레이싱 센서 기반 자동순찰 (`_patrol_loop()` 내부 교체)
- 실제 초음파 센서 기반 안전정지 (`_check_obstacle()` 내부 교체, 현재는 항상 False 반환하는 stub)
- `raspbot.py` 자동시작 영구 비활성화 (매 부팅마다 수동 kill 중)
- 로봇 배터리 재충전 후 모터 관련 나머지 테스트(Right/Stop 웹 경로) 마무리
- 조은수 Vision 코드와 실제 연결 (카메라 입력 파이프라인은 이제 준비 완료)

## ⚠️ 팀 내 확인 필요

- 초음파 안전정지 거리(`OBSTACLE_STOP_DISTANCE_CM = 20`)는 코드상 자리표시자 값이며, 실물 센서 테스트 후 팀 협의로 확정해야 합니다.
