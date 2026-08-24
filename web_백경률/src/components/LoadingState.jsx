export default function LoadingState({ label = '불러오는 중…' }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div className="skeleton skeleton--photo" />
      <div className="skeleton skeleton--line" style={{ width: '70%' }} />
      <div className="skeleton skeleton--line" style={{ width: '45%' }} />
    </div>
  )
}
