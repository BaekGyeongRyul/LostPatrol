// lost_items.status DB 값 <-> 화면 표시 매핑
// DB 값은 PROJECT_PLAN.md 기준으로 고정한다 (다른 팀원의 Python/Pi 코드가 이 값에 의존함).
export const LOST_ITEM_STATUS = {
  PENDING_ANALYSIS: 'pending_analysis',
  NEW: 'new',
  CONFIRMED: 'confirmed',
  RESOLVED: 'resolved',
  REJECTED: 'rejected',
}

export const LOST_ITEM_STATUS_LABEL = {
  [LOST_ITEM_STATUS.PENDING_ANALYSIS]: 'AI 분석 중',
  [LOST_ITEM_STATUS.NEW]: '확인 필요',
  [LOST_ITEM_STATUS.CONFIRMED]: '보관 중',
  [LOST_ITEM_STATUS.RESOLVED]: '반환 완료',
  [LOST_ITEM_STATUS.REJECTED]: '반려',
}

// StatusBadge 등에서 색상 톤을 고를 때 사용
export const LOST_ITEM_STATUS_TONE = {
  [LOST_ITEM_STATUS.PENDING_ANALYSIS]: 'neutral',
  [LOST_ITEM_STATUS.NEW]: 'amber',
  [LOST_ITEM_STATUS.CONFIRMED]: 'blue',
  [LOST_ITEM_STATUS.RESOLVED]: 'green',
  [LOST_ITEM_STATUS.REJECTED]: 'red',
}

// 관리자가 상세 페이지에서 수동으로 전환할 수 있는 상태만 노출한다.
export const MANUAL_STATUS_OPTIONS = [
  LOST_ITEM_STATUS.NEW,
  LOST_ITEM_STATUS.CONFIRMED,
  LOST_ITEM_STATUS.RESOLVED,
  LOST_ITEM_STATUS.REJECTED,
]

export const LOST_ITEM_STATUS_FILTERS = [
  { value: 'all', label: '전체' },
  { value: LOST_ITEM_STATUS.NEW, label: '확인 필요' },
  { value: LOST_ITEM_STATUS.CONFIRMED, label: '보관 중' },
  { value: LOST_ITEM_STATUS.RESOLVED, label: '반환 완료' },
  { value: LOST_ITEM_STATUS.REJECTED, label: '반려' },
]

export const ITEM_TYPE_LABEL = {
  backpack: '가방(백팩)',
  handbag: '핸드백',
  suitcase: '캐리어',
  wallet: '지갑',
  bottle: '물병',
  unknown: '미분류',
}

export const ITEM_TYPE_FILTERS = [
  { value: 'all', label: '전체 종류' },
  { value: 'backpack', label: 'Backpack' },
  { value: 'wallet', label: 'Wallet' },
  { value: 'bottle', label: 'Bottle' },
  { value: 'handbag', label: 'Handbag' },
  { value: 'suitcase', label: 'Suitcase' },
]

// robot_status.state DB 값 -> 표시 라벨
export const ROBOT_STATE_LABEL = {
  idle: 'IDLE',
  moving: 'MOVING',
  stopped: 'STOPPED',
  camera_error: 'CAMERA ERROR',
  offline: 'OFFLINE',
}

// updated_at 이 이 시간(ms) 이상 지나면 웹에서 자체적으로 OFFLINE 판단 (PROJECT_PLAN 5.3)
export const ROBOT_OFFLINE_THRESHOLD_MS = 15000

export function isRobotOffline(updatedAt) {
  if (!updatedAt) return true
  const updatedMs = new Date(updatedAt).getTime()
  if (Number.isNaN(updatedMs)) return true
  return Date.now() - updatedMs > ROBOT_OFFLINE_THRESHOLD_MS
}

export function formatItemType(itemType) {
  return ITEM_TYPE_LABEL[itemType] ?? itemType ?? '미분류'
}

export function formatConfidence(confidence) {
  if (confidence === null || confidence === undefined) return '—'
  return `${Math.round(confidence * 100)}%`
}
