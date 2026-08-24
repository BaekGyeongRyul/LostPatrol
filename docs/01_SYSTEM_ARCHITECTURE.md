# 01. SYSTEM ARCHITECTURE

LostPatrol은 공공장소 AI 분실물 탐색 · 자동 등록 순찰 로봇 시스템입니다.

## 전체 구조

```
[Web]                         [Supabase]                    [Raspberry Pi / Razbot]
React + Vite                  robot_commands                 실제 로봇 동작
LostPatrol 관제 대시보드  ───▶ robot_status         ◀───▶     (모터 / 라인트레이싱 /
(web-redesign)                lost_items                      초음파 센서 / 카메라 / heartbeat)
                               Storage: lost-item-photos
                                      ▲
                                      │
                              [OpenCV + Roboflow + YOLO]
                              분실물 객체 감지 (umbrella / bottle / backpack)
```

- **Web ↔ Supabase**: 연동 테스트 완료 (아래 "현재 검증된 항목" 참고)
- **Supabase ↔ Raspberry Pi**: 이번 전달 패키지 기준으로 이윤정 담당자가 연결
- **Supabase ↔ OpenCV/YOLO**: 이번 전달 패키지 기준으로 조은수 담당자가 연결

Web과 Raspberry Pi, Web과 AI 파이프라인은 서로 직접 통신하지 않습니다. **Supabase가 유일한 중앙 데이터 허브**이며, 모든 컴포넌트는 Supabase의 테이블/Storage 규격(`02_SUPABASE_DATA_CONTRACT.md`)을 통해서만 상호작용합니다.

## 현재 검증된 항목 (Web ↔ Supabase)

1. 웹 Forward 클릭 → `robot_commands`에 `command=forward, status=pending` INSERT 성공
2. 웹 PATROL START 클릭 → `command=patrol_start, status=pending` INSERT 성공
3. 웹 PATROL STOP 클릭 → `command=patrol_stop, status=pending` INSERT 성공
4. `robot_status.updated_at` 기준 웹 ONLINE/OFFLINE 표시 정상 동작
5. 15초 이상 heartbeat 없으면 OFFLINE 처리 확인
6. `lost_items` 데이터 웹에서 실제 SELECT 확인
7. 웹에서 분실물 상태 변경 → `lost_items.status` 실제 UPDATE 확인

## 아직 연결되지 않은 항목 (팀원 작업 대상)

- Raspberry Pi가 `robot_commands`를 폴링해서 실제로 로봇을 움직이는 부분 (이윤정)
- Raspberry Pi가 `robot_status`에 5초마다 heartbeat를 쓰는 부분 (이윤정)
- 라인트레이싱 자동순찰(`patrol_start`/`patrol_stop`) 실제 동작 (이윤정)
- 초음파 센서 장애물 안전 정지 (이윤정)
- OpenCV/YOLO 객체 감지 → `lost_items` INSERT, 사진 → Storage 업로드 (조은수)

## ⚠️ 통합 전 반드시 확인해야 할 사항 (읽기 전용 점검 결과)

이번 패키지를 만들면서 Supabase 구조를 **읽기 전용**으로 점검한 결과, 아래 사항이 확인되었습니다. 이는 코드 버그가 아니라 "RLS(Row Level Security) 권한 설계상 아직 막혀 있는 부분"이며, 임의로 수정하지 않고 그대로 보고합니다.

- 현재 `anon`(웹이 쓰는 publishable key) 권한으로는 `robot_commands`에 대해 **SELECT, INSERT만 가능하고 UPDATE 정책이 없습니다.** 즉 Raspberry Pi가 anon key로는 명령 완료 후 `status`/`executed_at`을 업데이트할 수 없습니다.
- `robot_status`도 `anon`은 **SELECT만 가능하고 UPDATE 정책이 없습니다.** Raspberry Pi가 anon key로는 heartbeat(`updated_at`) 갱신이 불가능합니다.
- `storage.objects`(버킷 `lost-item-photos`)에는 **RLS 정책이 아예 하나도 없습니다.** 버킷 자체는 `public=true`라서 웹에서 사진을 "보는 것"(공개 URL)은 되지만, anon key로 사진을 "업로드"하는 것은 막혀 있습니다.

**권장 해결 방향 (팀 협의 필요, 이번 작업에서 임의로 적용하지 않음):**
Raspberry Pi와 OpenCV/YOLO 쪽은 브라우저가 아닌 신뢰된 서버/디바이스 코드이므로, 웹처럼 anon/publishable key를 쓰지 말고 **Supabase의 `service_role` key를 각자의 로컬 `.env`에만 저장해서 사용**하는 것을 권장합니다. `service_role` key는 RLS를 우회하므로 위 UPDATE/INSERT 제한과 무관하게 동작합니다. 이 키는 **절대 web-redesign이나 Git 저장소에 넣지 않습니다.** (자세한 내용은 `04_ENV_AND_SECURITY_GUIDE.md` 참고)

만약 팀에서 "Pi/AI도 anon key만 쓰고 싶다"고 결정하면, `robot_commands`/`robot_status`/`storage.objects`에 대한 추가 RLS 정책이 필요하며, 이는 팀 전체 협의 후 진행해야 합니다.

## 관련 프로젝트 문서

- `PROJECT_PROPOSAL.md`, `PROJECT_PLAN.md` (팀프로젝트 루트) — 서비스 기획 및 최초 스키마 기준
- `TEAM_INTEGRATION_GUIDE.md` (이 폴더 및 팀프로젝트 루트) — Robot Command/Supabase 연동 요약
