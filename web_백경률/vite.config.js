import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  // 기본 프로덕션 빌드(GitHub Pages, `npm run build`)만 저장소 하위 경로(/LostPatrol/)를 base로 쓴다.
  // dev 서버와 standalone(dist-share, 파일 더블클릭 공유용) 빌드는 기존 그대로 상대경로 유지.
  base: mode === 'production' ? '/LostPatrol/' : './',
  // mode "standalone" (npm run build:share)는 JS/CSS를 전부 하나의 index.html에 inline해서
  // 서버 없이 파일을 더블클릭하거나 이메일/메신저로 그대로 공유해도 열리는 빌드를 만든다.
  plugins: [react(), mode === 'standalone' && viteSingleFile()].filter(Boolean),
}))
