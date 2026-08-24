# 04. ENV & SECURITY GUIDE

## Public 값 vs Secret 값 구분

Supabase는 키 성격이 완전히 다른 두 종류가 있습니다. 이 둘을 혼동하면 보안 사고로 이어지므로 반드시 구분하세요.

| 구분 | 예시 | 성격 | 사용처 |
|---|---|---|---|
| **Publishable / anon key** | `sb_publishable_...` (또는 구형 `eyJ...` JWT, role: anon) | **공개 가능.** RLS(Row Level Security)가 실제 방어선이며, 이 키만으로는 RLS가 허용한 범위(현재: 각 테이블 SELECT/일부 INSERT·UPDATE)만 할 수 있음 | 웹(`web-redesign`)의 `.env.local` — 브라우저에 그대로 노출되어도 됨(빌드 결과물에도 포함됨) |
| **service_role key** | Supabase 대시보드 > Project Settings > API에서 확인 | **절대 비공개.** RLS를 완전히 우회해서 모든 테이블에 무제한 접근 가능 | Raspberry Pi, OpenCV/YOLO 스크립트처럼 신뢰된 서버/디바이스 쪽 로컬 `.env`에서만 사용. **절대 웹 프로젝트, 브라우저 코드, Git에 넣지 않음** |

`web-redesign`은 이미 publishable key만 사용하도록 되어 있습니다(`src/lib/supabaseClient.js`). 이 구조는 그대로 유지하세요.

## .env 규칙

- 실제 값이 들어간 `.env`, `.env.local` 파일은 **Git에 절대 커밋하지 않습니다.** (`web-redesign/.gitignore`에 이미 `.env.*` 패턴으로 제외되어 있음 — 각자 프로젝트에도 동일하게 설정하세요)
- 이 전달 패키지(`LostPatrol_TEAM_HANDOFF`)에는 값이 채워진 `.env`/`.env.local`을 **넣지 않았습니다.** `ENV_EXAMPLE/.env.example`은 값이 비어있는 템플릿만 있습니다.
- 이윤정/조은수는 각자 자신의 프로젝트 폴더에 `.env`를 새로 만들고, Supabase 대시보드에서 본인이 직접 URL과 필요한 key를 발급/확인해서 채워 넣으세요.
- Raspberry Pi/AI 스크립트용 `.env` 예시:
  ```
  SUPABASE_URL=https://uityxtduglbshnvkstvx.supabase.co
  SUPABASE_SERVICE_ROLE_KEY=<Supabase 대시보드에서 본인이 직접 확인>
  ```
  이 파일은 각자 로컬에만 두고, `.gitignore`에 반드시 추가하세요.

## 이번 패키지 Secret 검사 결과

`LostPatrol_TEAM_HANDOFF` 폴더 전체를 아래 기준으로 검사했습니다.

- `service_role` / `SERVICE_ROLE` 문자열 검색 → **실제 키 값 없음.** `.env.example`과 `README.md`에 "SERVICE_ROLE_KEY를 넣지 말라"는 **경고 문구**로만 등장 (안전)
- `secret` 문자열 검색 → `FINAL_WEB/dist-share/index.html` 안에서 일부 매치가 나오지만, 전부 번들에 포함된 `@supabase/supabase-js` SDK **라이브러리 내부 코드**(`regenerateClientSecret` 같은 함수명, `sb_secret_`/`sb_temp_` 접두사를 구분하는 SDK 로직)이며 실제 키 값이 아님
- `.env.local` 파일 → **포함되지 않음** (`FINAL_WEB/SOURCE`, `ENV_EXAMPLE` 어디에도 없음)
- JWT(`eyJhbGciOi...`) 실키 → **포함되지 않음** (현재 빌드는 legacy JWT anon key가 아니라 새 publishable key 형식만 사용)
- `sb_publishable_...` 값과 프로젝트 URL(`uityxtduglbshnvkstvx.supabase.co`) → `dist-share/index.html`에 **포함되어 있음.** 이는 publishable key라 공개되어도 안전하며, 웹 앱이 정상 동작하려면 원래 포함되어야 하는 값입니다.

**결론: service_role key, 실제 비밀번호, `.env.local` 등 진짜 비밀 정보는 이 패키지에 없습니다.** 포함된 키는 모두 "공개돼도 되는" publishable key뿐입니다.

## 담당자별 체크리스트

- [ ] 내 `.env`/`.env.local`을 Git에 커밋하지 않았는가
- [ ] `service_role` key를 코드에 직접 문자열로 박아넣지 않았는가 (반드시 환경변수로)
- [ ] `service_role` key를 팀 단체방/이슈/커밋 메시지에 붙여넣지 않았는가
- [ ] 새로 만든 프로젝트 폴더에도 `.gitignore`로 `.env`류를 제외했는가
