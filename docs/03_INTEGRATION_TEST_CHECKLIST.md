# 03. INTEGRATION TEST CHECKLIST

각 담당자가 자기 코드를 연결한 뒤, 아래 순서대로 통합 테스트를 진행하세요. 웹은 `FINAL_WEB/dist-share/index.html`(또는 `web-redesign`을 `npm run dev`로 실행)로 열고, Supabase Table Editor로 실제 행 변화를 같이 확인하면 좋습니다.

| # | 테스트 | Expected Result | 담당자 | 완료 |
|---|---|---|---|---|
| 1 | Web에서 **Forward** 클릭 → `robot_commands` INSERT → Raspberry Pi가 감지 | 로봇이 실제로 직진하고, 처리 후 해당 행 `status`가 갱신됨 | 이윤정 | ☐ |
| 2 | Web에서 **Left** 클릭 | 로봇이 **제자리에서** 좌회전 (전진하며 도는 것이 아님) | 이윤정 | ☐ |
| 3 | Web에서 **Right** 클릭 | 로봇이 **제자리에서** 우회전 | 이윤정 | ☐ |
| 4 | Web에서 **STOP** 클릭 | 로봇이 즉시 정지 | 이윤정 | ☐ |
| 5 | Web에서 **PATROL START** 클릭 | 라인트레이싱 자동순찰이 시작됨 | 이윤정 | ☐ |
| 6 | Web에서 **PATROL STOP** 클릭 | 자동순찰이 종료되고 정지 상태로 전환 | 이윤정 | ☐ |
| 7 | Pi가 5초마다 `robot_status.updated_at` 갱신 | 웹 상태 배지가 계속 **ONLINE** 유지 | 이윤정 | ☐ |
| 8 | Pi 연결/heartbeat 중단 | 마지막 갱신 후 **15초 뒤** 웹이 자동으로 **OFFLINE** 표시 | 이윤정 | ☐ |
| 9 | 자동순찰 중 초음파 센서로 장애물 감지 | 설정된 거리 이내 장애물 발견 시 로봇이 **안전 정지** (회피 아님) | 이윤정 | ☐ |
| 10 | 카메라 앞에 umbrella / bottle / backpack 노출 | YOLO가 탐지하고(2~3회 연속 검출 확인 후) `lost_items`에 새 행 INSERT (`status='new'`) | 조은수 | ☐ |
| 11 | 위 탐지 시 촬영된 이미지 | `lost-item-photos` 버킷에 업로드되고, 그 공개 URL이 `lost_items.image_url`에 저장되어 **웹 화면에 실제 이미지로 표시**됨 | 조은수 | ☐ |
| 12 | 웹 분실물 상세 화면에서 상태 변경(예: 확인 필요 → 보관 중) | `lost_items.status`가 실제로 UPDATE됨 (이미 검증 완료, 회귀 확인용) | Web 담당 | ☐ |

## 테스트 팁

- 각 테스트 전/후로 Supabase Table Editor에서 `robot_commands`/`robot_status`/`lost_items`를 직접 열어두면 어느 단계에서 막히는지 빠르게 파악할 수 있습니다.
- 1~9번 테스트는 `04_ENV_AND_SECURITY_GUIDE.md`에 안내된 대로 Pi 쪽이 `service_role` key로 연결되어 있어야 정상 동작합니다(현재 `robot_commands`/`robot_status`에 anon UPDATE 권한이 없기 때문입니다 — 자세한 내용은 `02_SUPABASE_DATA_CONTRACT.md` 참고).
- 10~11번 테스트도 마찬가지로 조은수 쪽 업로드 스크립트가 `service_role` key를 쓰는지 먼저 확인하세요.
- confidence는 항상 0~1 사이 숫자인지, item_type/command 문자열에 오타가 없는지 함께 확인하세요.
