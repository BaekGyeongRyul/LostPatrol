import { fetchCameraFeed } from '../lib/patrolApi'
import { usePolling } from './usePolling'

export function useCameraFeed({ intervalMs = 10000 } = {}) {
  const { data, loading, error, refetch } = usePolling(fetchCameraFeed, { intervalMs })
  return { feed: data, loading, error, refetch }
}
