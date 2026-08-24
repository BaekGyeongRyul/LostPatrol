import { fetchLostItems } from '../lib/api'
import { usePolling } from './usePolling'

export function useLostItems({ intervalMs = 5000 } = {}) {
  const { data, loading, error, refetch } = usePolling(fetchLostItems, { intervalMs })
  return { items: data ?? [], loading, error, refetch }
}
