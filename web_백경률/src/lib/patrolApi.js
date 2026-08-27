import { supabase } from './supabaseClient'
import { isDemoMode } from './api'
import { mockSafetyStatus, mockPatrolEvents, mockCameraFeed } from '../data/mockPatrolData'

// lost_items / robot_commands / robot_status 와 마찬가지로, 안전 감지(safety_status)와
// 순찰 이벤트(patrol_events)도 이제 Supabase 테이블이 연동되어 있다(이윤정 담당,
// robot_이윤정/mock_controller/safety_monitor.py·motion_monitor.py 참고). Demo 모드
// (Supabase 환경변수 미설정)에서는 기존처럼 Mock 데이터를 그대로 사용한다.
// 카메라 스트림(patrol_events 이후 추가 예정)만 아직 대응 테이블이 없어 Mock을 유지한다.

function mapSafetyStatusRow(row) {
  return {
    fire: {
      severity: row.fire_severity,
      flameDetected: row.flame_detected,
      temperatureC: row.temperature_c,
    },
    motion: {
      severity: row.motion_severity,
      personDetected: row.person_detected,
    },
    sound: {
      severity: row.sound_severity,
      level: row.sound_level,
    },
  }
}

export async function fetchSafetyStatus() {
  if (isDemoMode) {
    return mockSafetyStatus
  }
  const { data, error } = await supabase.from('safety_status').select('*').eq('id', 1).single()
  if (error) throw error
  return mapSafetyStatusRow(data)
}

export async function fetchPatrolEvents(limit = 10) {
  if (isDemoMode) {
    return [...mockPatrolEvents]
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, limit)
  }
  const { data, error } = await supabase
    .from('patrol_events')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return data
}

export async function fetchCameraFeed() {
  // TODO: Razbot 카메라 스트리밍 서버 준비 후 실제 cameraStreamUrl(또는 스냅샷 URL)로 교체
  return mockCameraFeed
}
