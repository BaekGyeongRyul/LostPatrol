import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function ErrorState({ message = '데이터를 불러오지 못했습니다.', onRetry }) {
  return (
    <div className="error-state" role="alert">
      <AlertTriangle size={22} strokeWidth={1.8} />
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="btn btn--ghost btn--sm" onClick={onRetry}>
          <RefreshCw size={14} />
          다시 시도
        </button>
      )}
    </div>
  )
}
