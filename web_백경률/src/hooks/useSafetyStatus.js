import { fetchSafetyStatus } from '../lib/patrolApi'
import { usePolling } from './usePolling'

export function useSafetyStatus({ intervalMs = 5000 } = {}) {
  const { data, loading, error, refetch } = usePolling(fetchSafetyStatus, { intervalMs })
  return { safety: data, loading, error, refetch }
}
