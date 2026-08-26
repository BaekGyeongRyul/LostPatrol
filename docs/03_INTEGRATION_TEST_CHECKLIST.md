# 03. INTEGRATION TEST CHECKLIST

각 담당자가 자기 코드를 연결한 뒤, 아래 순서대로 통합 테스트를 진행하세요. 웹은 `FINAL_WEB/dist-share/index.html`(또는 `web-redesign`을 `npm run dev`로 실행)로 열고, Supabase Table Editor로 실제 행 변화를 같이 확인하면 좋습니다.

| # | 테스트 | Expected Result | 담당자 | 완료 |
|---|---|---|---|---|
| 1 | Web에서 **Forward** 클릭 → `robot_commands` INSERT → Raspberry Pi가 감지 | 로봇이 실제로 직진하고, 처리 후 해당 행 `status`가 갱신됨 | 이윤정 | ☑ (2026.08.26 실물로 확인) |
| 2 | Web에서 **Left** 클릭 | 로봇이 **제자리에서** 좌회전 (전진하며 도는 것이 아님) | 이윤정 | ☑ (2026.08.26 실물 확인, 회전시간 0.3초로 튜닝) |
| 3 | Web에서 **Right** 클릭 | 로봇이 **제자리에서** 우회전 | 이윤정 | ☑ (2026.08.26 실물 확인) |
| 4 | Web에서 **STOP** 클릭 | 로봇이 즉시 정지 | 이윤정 | ☑ (2026.08.26 이동 중 STOP 눌러서 즉시 정지 확인) |
| 5 | Web에서 **PATROL START** 클릭 | 라인트레이싱 자동순찰이 시작됨 | 이윤정 | ☐ |
| 6 | Web에서 **PATROL STOP** 클릭 | 자동순찰이 종료되고 정지 상태로 전환 | 이윤정 | ☐ |
| 7 | Pi가 5초마다 `robot_status.updated_at` 갱신 | 웹 상태 배지가 계속 **ONLINE** 유지 | 이윤정 | ☑ (2026.08.25 24분 무중단 테스트로 검증, 2026.08.26 실물 Pi에서도 확인) |
| 8 | Pi 연결/heartbeat 중단 | 마지막 갱신 후 **15초 뒤** 웹이 자동으로 **OFFLINE** 표시 | 이윤정 | ☐ |
| 9 | 자동순찰 중 초음파 센서로 장애물 감지 | 설정된 거리 이내 장애물 발견 시 로봇이 **안전 정지** (회피 아님) | 이윤정 | ☐ |
| 10 | 카메라 앞에 umbrella / bottle / backpack 노출 | YOLO가 탐지하고(2~3회 연속 검출 확인 후) `lost_items`에 새 행 INSERT (`status='new'`) | 조은수 | 🔶 로직은 검증됨(2026.08.26, 이윤정: `vision_조은수/detect_and_register.py` 초안 작성, 학습용 테스트 이미지로 3종 감지+연속2회+INSERT 실제 확인) — **실물 카메라로 진짜 물체 비추는 최종 테스트는 아직** |
| 11 | 위 탐지 시 촬영된 이미지 | `lost-item-photos` 버킷에 업로드되고, 그 공개 URL이 `lost_items.image_url`에 저장되어 **웹 화면에 실제 이미지로 표시**됨 | 조은수 | 🔶 위와 동일 — Storage 업로드+URL 저장 로직은 실제 Supabase로 확인됨, 실물 카메라 기준 최종 확인 필요 |
| 12 | 웹 분실물 상세 화면에서 상태 변경(예: 확인 필요 → 보관 중) | `lost_items.status`가 실제로 UPDATE됨 (이미 검증 완료, 회귀 확인용) | Web 담당 | ☐ |

## 테스트 팁

- 각 테스트 전/후로 Supabase Table Editor에서 `robot_commands`/`robot_status`/`lost_items`를 직접 열어두면 어느 단계에서 막히는지 빠르게 파악할 수 있습니다.
- (업데이트 2026.08.25) 강사 피드백에 따라 service_role 대신 **anon(public) key**로 최종 전환했습니다. `robot_commands`/`robot_status`/`safety_status`/`patrol_events`/`lost-item-photos`/`lost_items` 전부 anon 역할에 필요한 범위만큼 제한적인 RLS 정책이 추가되어 있으니, 1~11번 테스트는 anon key만으로 정상 동작합니다.
- confidence는 항상 0~1 사이 숫자인지, item_type/command 문자열에 오타가 없는지 함께 확인하세요.
