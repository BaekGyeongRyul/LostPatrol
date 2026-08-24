import { LOST_ITEM_STATUS_LABEL, LOST_ITEM_STATUS_TONE } from '../lib/statusMap'

export default function StatusBadge({ status }) {
  const label = LOST_ITEM_STATUS_LABEL[status] ?? status
  const tone = LOST_ITEM_STATUS_TONE[status] ?? 'neutral'
  return <span className={`badge badge--${tone}`}>{label}</span>
}
