import { ROBOT_STATE_LABEL } from '../lib/statusMap'

export default function RobotStatusPill({ status, offline, loading }) {
  if (loading && !status) {
    return (
      <span className="robot-pill robot-pill--neutral">
        <span className="robot-pill__dot" />
        확인 중…
      </span>
    )
  }

  if (offline) {
    return (
      <span className="robot-pill robot-pill--offline">
        <span className="robot-pill__dot" />
        OFFLINE
      </span>
    )
  }

  const state = status?.state ?? 'idle'
  const tone = state === 'moving' ? 'moving' : state === 'camera_error' ? 'error' : 'online'
  const label = ROBOT_STATE_LABEL[state] ?? state.toUpperCase()

  return (
    <span className={`robot-pill robot-pill--${tone}`}>
      <span className="robot-pill__dot" />
      {label}
    </span>
  )
}
