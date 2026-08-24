import { useCallback, useEffect, useRef, useState } from 'react'

// 지정한 fetcher를 즉시 1회 호출하고, intervalMs 마다 조용히 다시 호출해 데이터를 최신 상태로 유지한다.
// (PROJECT_PLAN 상 Supabase Realtime은 "가능하면 구현" 항목이라 기본은 폴링 방식으로 구현한다.)
export function usePolling(fetcher, { intervalMs = 5000, deps = [] } = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const load = useCallback(async (isBackground) => {
    if (!isBackground) setLoading(true)
    try {
      const result = await fetcherRef.current()
      setData(result)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      if (!isBackground) setLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    let intervalId

    const run = async (isBackground) => {
      if (cancelled) return
      await load(isBackground)
    }

    run(false)
    intervalId = setInterval(() => run(true), intervalMs)

    return () => {
      cancelled = true
      clearInterval(intervalId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading, error, refetch: () => load(false) }
}
