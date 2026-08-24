import { fetchPatrolEvents } from '../lib/patrolApi'
import { usePolling } from './usePolling'

export function usePatrolEvents({ limit = 10, intervalMs = 5000 } = {}) {
  const { data, loading, error, refetch } = usePolling(() => fetchPatrolEvents(limit), {
    intervalMs,
  })
  return { events: data ?? [], loading, error, refetch }
}
