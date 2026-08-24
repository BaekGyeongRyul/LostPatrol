import { fetchRobotStatus } from '../lib/api'
import { isRobotOffline } from '../lib/statusMap'
import { usePolling } from './usePolling'

// robot_status.updated_at 이 15초 이상 지나면 웹에서 자체적으로 OFFLINE 판단 (PROJECT_PLAN 5.3)
export function useRobotStatus({ intervalMs = 2000 } = {}) {
  const { data, loading, error, refetch } = usePolling(fetchRobotStatus, { intervalMs })
  const offline = data ? isRobotOffline(data.updated_at) : true
  return { status: data, offline, loading, error, refetch }
}
