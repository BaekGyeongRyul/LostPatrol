import { mockSafetyStatus, mockPatrolEvents, mockCameraFeed } from '../data/mockPatrolData'

// lost_items / robot_commands / robot_status 와 달리, 안전 감지·순찰 이벤트·카메라 스트림은
// 아직 Supabase에 대응 테이블이 없다(센서/카메라 하드웨어가 아직 연결되지 않았기 때문).
// 그래서 이 함수들은 지금은 항상 Mock 데이터를 반환하지만, lib/api.js와 동일한 형태의
// 비동기 함수로 만들어 두었다. 나중에 테이블이 생기면 이 함수 내부만
// Supabase 조회로 바꾸면 되고, 이 함수를 호출하는 hooks/컴포넌트는 수정할 필요가 없다.

export async function fetchSafetyStatus() {
  // TODO: Arduino(FLAME + LM35DZ) / Sound Sensor 연동 후 아래로 교체
  // const { data, error } = await supabase.from('safety_status').select('*').single()
  return mockSafetyStatus
}

export async function fetchPatrolEvents(limit = 10) {
  // TODO: `patrol_events` 테이블(id, event_type, location, message, created_at, severity)
  // 생성 후 아래로 교체
  // const { data, error } = await supabase
  //   .from('patrol_events')
  //   .select('*')
  //   .order('created_at', { ascending: false })
  //   .limit(limit)
  return [...mockPatrolEvents]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, limit)
}

export async function fetchCameraFeed() {
  // TODO: Razbot 카메라 스트리밍 서버 준비 후 실제 cameraStreamUrl(또는 스냅샷 URL)로 교체
  return mockCameraFeed
}
