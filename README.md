# LostPatrol

🌐 **실제 웹사이트:** https://BaekGyeongRyul.github.io/LostPatrol/

공공장소 AI 분실물 탐색 · 자동 등록 순찰 로봇 프로젝트입니다.

Web 관제 대시보드 + Supabase(DB/Storage) + Raspberry Pi(Razbot) + OpenCV/Roboflow/YOLO 로 구성되며, Supabase가 모든 컴포넌트를 잇는 중앙 데이터 허브입니다.

```
[Web] ── Supabase(robot_commands / robot_status / lost_items / Storage) ── [Raspberry Pi / Razbot]
                              ▲
                              │
                    [OpenCV + Roboflow + YOLO]
```

## Live Web

GitHub Pages: https://BaekGyeongRyul.github.io/LostPatrol/

`main` 브랜치에 push되면 GitHub Actions(`.github/workflows/deploy-pages.yml`)가 자동으로 `web_백경률`을 빌드해서 위 주소에 배포합니다.

## 폴더 구조

```
LostPatrol_Git/
├─ web_백경률/     React + Vite 웹 관제 대시보드 (최종 확정 버전 = web-redesign 기준)
├─ robot_이윤정/   Raspberry Pi / Razbot 로봇 제어 코드
├─ vision_조은수/  OpenCV / Roboflow / YOLO 분실물 탐지 코드
├─ docs/    시스템 구조, Supabase 데이터 규격, 담당자별 연동 가이드
├─ README.md
├─ .gitignore
└─ .env.example
```

## 역할 분담

| 담당자 | 역할 | 관련 폴더 |
|---|---|---|
| 백경률 | Web + Supabase | `web_백경률/` |
| 이윤정 | Raspberry Pi + Razbot + Line Tracking + Ultrasonic | `robot_이윤정/` |
| 조은수 | OpenCV + Roboflow + YOLO | `vision_조은수/` |

먼저 읽어야 할 문서: `docs/00_README_FIRST.md`

## Robot Command 규격 (고정, 임의 변경 금지)

| command | 의미 |
|---|---|
| `forward` | 직진 |
| `backward` | 후진 |
| `left` | **제자리 좌회전** |
| `right` | **제자리 우회전** |
| `stop` | 즉시 정지 |
| `capture` | 카메라 촬영 |
| `patrol_start` | 라인트레이싱 기반 자동순찰 시작 |
| `patrol_stop` | 자동순찰 종료 |

## Heartbeat

- Raspberry Pi: `robot_status.updated_at`을 **5초마다** 갱신
- Web: 마지막 `updated_at`이 **15초 이상** 지나면 자동으로 OFFLINE 표시

## 분실물 Class (정확히 3종, 고정)

- `umbrella` (우산)
- `bottle` (물병)
- `backpack` (가방)

## 자세한 내용

- 전체 시스템 구조: `docs/01_SYSTEM_ARCHITECTURE.md`
- Supabase 테이블/RLS 데이터 규격: `docs/02_SUPABASE_DATA_CONTRACT.md`
- 통합 테스트 체크리스트: `docs/03_INTEGRATION_TEST_CHECKLIST.md`
- 환경변수/보안 가이드: `docs/04_ENV_AND_SECURITY_GUIDE.md`

## 실행 방법 (web_백경률/)

```bash
cd web_백경률
npm install
cp .env.example .env.local   # 값 채우기 (VITE_SUPABASE_URL, VITE_SUPABASE_PUBLISHABLE_KEY)
npm run dev
```

`.env.local`은 Git에 커밋하지 않습니다 (`.gitignore`에 이미 제외되어 있음).

## 보안 원칙

- `service_role` key, 실제 비밀번호, 개인 인증정보는 이 저장소 어디에도 넣지 않습니다.
- `.env`, `.env.local` 등 실제 값이 채워진 환경변수 파일은 커밋하지 않습니다 (`.env.example`만 커밋).
- robot_이윤정/vision_조은수 코드가 사용하는 `SUPABASE_SERVICE_ROLE_KEY`는 각자 로컬 `.env`에만 두세요.
