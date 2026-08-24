import { supabase, isSupabaseConfigured } from './supabaseClient'
import { mockStore } from '../data/mockStore'

// 이 파일은 Supabase 연결 여부에 따라 실제 DB / 데모(Mock) 데이터를 동일한 함수 시그니처로 제공한다.
// UI 컴포넌트는 이 함수들만 호출하며, Supabase 클라이언트를 직접 다루지 않는다.
export const isDemoMode = !isSupabaseConfigured

const VALID_ROBOT_COMMANDS = ['forward', 'backward', 'left', 'right', 'stop', 'capture', 'patrol_start', 'patrol_stop']

export async function fetchLostItems() {
  if (isDemoMode) {
    return mockStore.getLostItems()
  }
  const { data, error } = await supabase
    .from('lost_items')
    .select('*')
    .order('detected_at', { ascending: false })
  if (error) throw error
  return data
}

export async function fetchLostItemById(id) {
  if (isDemoMode) {
    const item = mockStore.getLostItemById(id)
    if (!item) throw new Error('분실물 정보를 찾을 수 없습니다.')
    return item
  }
  const { data, error } = await supabase.from('lost_items').select('*').eq('id', id).single()
  if (error) throw error
  return data
}

export async function updateLostItemStatus(id, status) {
  if (isDemoMode) {
    return mockStore.updateLostItemStatus(id, status)
  }
  const { data, error } = await supabase
    .from('lost_items')
    .update({ status })
    .eq('id', id)
    .select()
    .single()
  if (error) throw error
  return data
}

export async function fetchRobotStatus() {
  if (isDemoMode) {
    return mockStore.getRobotStatus()
  }
  const { data, error } = await supabase.from('robot_status').select('*').eq('id', 1).single()
  if (error) throw error
  return data
}

export async function fetchRecentRobotCommands(limit = 10) {
  if (isDemoMode) {
    return mockStore.getRobotCommands(limit)
  }
  const { data, error } = await supabase
    .from('robot_commands')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return data
}

export async function sendRobotCommand(command) {
  if (!VALID_ROBOT_COMMANDS.includes(command)) {
    throw new Error(`허용되지 않은 명령입니다: ${command}`)
  }
  if (isDemoMode) {
    return mockStore.sendRobotCommand(command)
  }
  const { data, error } = await supabase
    .from('robot_commands')
    .insert({ command, status: 'pending' })
    .select()
    .single()
  if (error) throw error
  return data
}
