import { fetchRecentRobotCommands } from '../lib/api'
import { usePolling } from './usePolling'

export function useRobotCommands({ limit = 8, intervalMs = 5000 } = {}) {
  const { data, loading, error, refetch } = usePolling(() => fetchRecentRobotCommands(limit), {
    intervalMs,
  })
  return { commands: data ?? [], loading, error, refetch }
}
