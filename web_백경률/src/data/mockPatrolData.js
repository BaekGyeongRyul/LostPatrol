import { SEVERITY } from '../lib/severity'

// 이 파일은 아직 실제로 연결되지 않은 안전 센서 / 순찰 이벤트 / 카메라 스트림을 위한
// Demo 전용 데이터다. 실제 하드웨어가 연결되기 전까지 Live Patrol 화면은 이 값만 사용한다.
//
// 향후 데이터 흐름:
//   Arduino(FLAME + LM35DZ, Sound Sensor) → Raspberry Pi 5 → Supabase → Web(Live Patrol)
//   Razbot 카메라 → Python Vision(person detection) → Supabase → Web(Live Patrol)
//
// 실제 연동 시에는 이 파일의 값을 지우지 말고, src/lib/patrolApi.js 안의 fetch 함수들만
// Supabase 조회로 교체하면 된다(호출하는 hooks/컴포넌트는 그대로 유지).

export const mockSafetyStatus = {
  fire: {
    severity: SEVERITY.NORMAL,
    flameDetected: false,
    temperatureC: 26.4,
  },
  motion: {
    severity: SEVERITY.NORMAL,
    personDetected: false,
  },
  sound: {
    severity: SEVERITY.NORMAL,
    level: 'low', // 'low' | 'high'
  },
}

const minutesAgo = (min) => new Date(Date.now() - min * 60 * 1000).toISOString()

// 향후 Supabase `patrol_events` 테이블과 동일한 컬럼 구조로 맞춰둔 Mock 데이터.
// { id, event_type, location, message, created_at, severity }
export const mockPatrolEvents = [
  {
    id: 1,
    event_type: 'patrol_start',
    location: 'A구역',
    message: '순찰 시작',
    created_at: minutesAgo(6),
    severity: SEVERITY.NORMAL,
  },
  {
    id: 2,
    event_type: 'motion_detected',
    location: 'A구역',
    message: '사람 감지',
    created_at: minutesAgo(4),
    severity: SEVERITY.WARNING,
  },
  {
    id: 3,
    event_type: 'loud_sound',
    location: 'B구역',
    message: '큰 소리 감지',
    created_at: minutesAgo(3),
    severity: SEVERITY.WARNING,
  },
  {
    id: 4,
    event_type: 'status_normal',
    location: 'B구역',
    message: '정상 상태 복귀',
    created_at: minutesAgo(2),
    severity: SEVERITY.NORMAL,
  },
]

// cameraStreamUrl이 비어 있으면 Live Patrol 화면은 "실시간 화면 송출 예정" 플레이스홀더를 보여준다.
// 실제 Razbot 카메라 스트리밍 주소(또는 스냅샷 이미지 URL)가 준비되면 이 값만 채우면 된다.
//
// 2026.08.27: 이윤정이 라즈베리파이에 MJPEG 스트리밍 서버(robot_이윤정/mock_controller/stream_server.py)를
// 만들어서 실물로 확인했다 (Pi에서 `python3 stream_server.py` 실행 → <img src="...">로 바로 재생됨).
// 다만 이 주소는 라즈베리파이의 "로컬 네트워크 IP"라서:
//   - Pi랑 같은 WiFi에 있는 사람만 볼 수 있음 (외부/다른 네트워크에서는 접속 안 됨)
//   - Pi가 재부팅되거나 WiFi를 새로 잡으면 IP가 바뀔 수 있음(고정 IP 아니면)
// 그래서 배포된 사이트에 그대로 박아두기보다, 데모 당일 그때그때 Pi의 실제 IP로
// 맞춰서 값을 넣는 걸 권장합니다 (`hostname -I`로 확인). 아래 값은 2026.08.27 로컬 테스트 당시 IP 예시.
export const mockCameraFeed = {
  cameraStreamUrl: 'http://192.168.0.67:8090/stream.mjpg',
  zone: 'A구역',
}
