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

## ⬜ 남은 과제

- 실제 Razbot 모터 제어 연동 (`YB_Pcb_Car.py` 라이브러리 연결 — `_move()` 내부 교체)
- 실제 라인트레이싱 센서 기반 자동순찰 (`_patrol_loop()` 내부 교체)
- 실제 초음파 센서 기반 안전정지 (`_check_obstacle()` 내부 교체, 현재는 항상 False 반환하는 stub)

**아직 실제 Razbot 모터/라인트레이싱/초음파 기능까지 모두 완성된 것은 아니며, 현재는 Mock Controller 단계에서 Supabase 연동 로직만 검증된 상태입니다.**

## ⚠️ 팀 내 확인 필요

- `HARDWARE_REFERENCE.md`(Yahboom 공식 자료 기준)에 정리된 내용에 따르면 실제 로봇 제어는 WebSocket이 아니라 I2C/GPIO 기반 로컬 파이썬 라이브러리 direct 호출 방식입니다. 좌/우 제자리 회전에 대응하는 정확한 함수명(`Car_Left`/`Car_Right` 등으로 추정)은 아직 실물 도착 후 라이브러리 코드에서 확인이 필요합니다.
- 초음파 안전정지 거리(`OBSTACLE_STOP_DISTANCE_CM = 20`)는 코드상 자리표시자 값이며, 실물 센서 테스트 후 팀 협의로 확정해야 합니다.
- 카메라 입력 장치가 Razbot 자체 카메라인지, 별도 ESP32-S3 Camera인지는 문서 간 표현이 엇갈립니다. `HARDWARE_REFERENCE.md`에는 ESP32-S3에 대한 언급이 없고, 조은수 담당자 전달 내용에서는 ESP32-S3 Camera가 언급되었습니다. 최종 카메라 입력 장치는 팀 내 하드웨어 구조 최종 확인이 필요합니다.
