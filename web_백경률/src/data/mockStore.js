import { initialMockLostItems } from './mockLostItems'

// 데모 모드(Supabase 미연결)에서 실제 DB처럼 동작하는 인메모리 저장소.
// 새로고침하면 초기화된다 — 목적은 UI 흐름 검증이지 영구 저장이 아니다.
let lostItems = initialMockLostItems.map((item) => ({ ...item }))
let nextItemId = 2000

let robotStatus = {
  id: 1,
  state: 'idle',
  last_command: null,
  updated_at: new Date().toISOString(),
}

let robotCommands = [
  { id: 1, command: 'stop', status: 'done', created_at: new Date(Date.now() - 8 * 60 * 1000).toISOString(), executed_at: new Date(Date.now() - 8 * 60 * 1000 + 500).toISOString() },
  { id: 2, command: 'forward', status: 'done', created_at: new Date(Date.now() - 9 * 60 * 1000).toISOString(), executed_at: new Date(Date.now() - 9 * 60 * 1000 + 500).toISOString() },
]
let nextCommandId = 3

function touchRobotHeartbeat() {
  robotStatus = { ...robotStatus, updated_at: new Date().toISOString() }
}

// 데모 모드에서도 로봇이 "살아있는" 것처럼 보이도록 주기적으로 하트비트를 갱신한다.
if (typeof window !== 'undefined') {
  setInterval(touchRobotHeartbeat, 4000)
}

export const mockStore = {
  getLostItems() {
    return [...lostItems].sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at))
  },
  getLostItemById(id) {
    return lostItems.find((item) => String(item.id) === String(id)) ?? null
  },
  updateLostItemStatus(id, status) {
    lostItems = lostItems.map((item) => (String(item.id) === String(id) ? { ...item, status } : item))
    return this.getLostItemById(id)
  },
  getRobotStatus() {
    return { ...robotStatus }
  },
  getRobotCommands(limit = 10) {
    return [...robotCommands]
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, limit)
  },
  sendRobotCommand(command) {
    const now = new Date().toISOString()
    const entry = { id: nextCommandId++, command, status: 'done', created_at: now, executed_at: now }
    robotCommands = [entry, ...robotCommands]

    const stateByCommand = {
      forward: 'moving',
      backward: 'moving',
      left: 'moving',
      right: 'moving',
      stop: 'stopped',
      capture: robotStatus.state,
    }
    robotStatus = {
      ...robotStatus,
      state: stateByCommand[command] ?? robotStatus.state,
      last_command: command,
      updated_at: now,
    }

    if (command === 'capture') {
      simulateCapture()
    }

    return entry
  },
}

function simulateCapture() {
  const types = ['backpack', 'wallet', 'bottle', 'handbag', 'suitcase']
  const type = types[Math.floor(Math.random() * types.length)]
  const now = new Date().toISOString()
  const newItem = {
    id: nextItemId++,
    image_url: null, // mockPhotoFor는 UI에서 lazy 처리
    item_type: type,
    description: null,
    confidence: null,
    detected_at: now,
    location: ['A구역', 'B구역', 'C구역', 'D구역'][Math.floor(Math.random() * 4)],
    status: 'pending_analysis',
    created_at: now,
  }
  lostItems = [newItem, ...lostItems]

  // 실제 파이프라인(Vision + Gemini 분석)을 흉내내어 잠시 후 분석 완료 상태로 전환한다.
  setTimeout(() => {
    lostItems = lostItems.map((item) =>
      item.id === newItem.id
        ? {
            ...item,
            confidence: 0.6 + Math.random() * 0.35,
            description: '데모 모드 자동 생성 설명 — 실제 연결 시 Gemini API 결과로 대체됩니다.',
            status: 'new',
          }
        : item,
    )
  }, 4000)
}
