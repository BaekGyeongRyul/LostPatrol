import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, MapPin, Clock } from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import LoadingState from '../components/LoadingState'
import ErrorState from '../components/ErrorState'
import { fetchLostItemById, updateLostItemStatus } from '../lib/api'
import { useToast } from '../hooks/useToast'
import {
  MANUAL_STATUS_OPTIONS,
  LOST_ITEM_STATUS,
  LOST_ITEM_STATUS_LABEL,
  formatItemType,
} from '../lib/statusMap'
import { formatDateTime } from '../lib/time'
import { mockPhotoFor } from '../data/mockImage'

export default function LostItemDetail() {
  const { id } = useParams()
  const showToast = useToast()
  const [item, setItem] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatingStatus, setUpdatingStatus] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchLostItemById(id)
      setItem(data)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const handleStatusChange = async (status) => {
    setUpdatingStatus(status)
    try {
      const updated = await updateLostItemStatus(id, status)
      setItem(updated)
      showToast(`상태를 "${LOST_ITEM_STATUS_LABEL[status]}"(으)로 변경했습니다.`, { tone: 'success' })
    } catch (err) {
      showToast(err.message ?? '상태 변경에 실패했습니다.', { tone: 'error' })
    } finally {
      setUpdatingStatus(null)
    }
  }

  if (loading) {
    return (
      <div className="page">
        <LoadingState label="분실물 정보를 불러오는 중…" />
      </div>
    )
  }

  if (error || !item) {
    return (
      <div className="page">
        <ErrorState message="분실물 정보를 찾을 수 없습니다." onRetry={load} />
      </div>
    )
  }

  const isPendingAnalysis = item.status === LOST_ITEM_STATUS.PENDING_ANALYSIS
  const photo = item.image_url ?? mockPhotoFor(item.item_type)

  return (
    <div className="page">
      <Link to="/lost-items" className="back-link">
        <ArrowLeft size={16} />
        Lost Items로 돌아가기
      </Link>

      <div className="detail-grid">
        <section className="detail-photo">
          <img src={photo} alt={formatItemType(item.item_type)} />
        </section>

        <section className="panel detail-panel">
          <div className="detail-panel__top">
            <h2>{formatItemType(item.item_type)}</h2>
            <StatusBadge status={item.status} />
          </div>

          <p className="detail-panel__description">
            {isPendingAnalysis
              ? 'AI가 이미지를 분석하고 있습니다. 잠시 후 자동으로 설명이 채워집니다.'
              : item.description || '설명 생성 실패 - 관리자 확인 필요'}
          </p>

          <dl className="detail-facts">
            <div>
              <dt>
                <Clock size={14} /> Detected Time
              </dt>
              <dd>{formatDateTime(item.detected_at)}</dd>
            </div>
            <div>
              <dt>
                <MapPin size={14} /> Location
              </dt>
              <dd>{item.location ?? '위치 미확인'}</dd>
            </div>
          </dl>

          <div className="detail-panel__status-change">
            <p className="detail-panel__status-label">상태 변경</p>
            {isPendingAnalysis ? (
              <p className="detail-panel__pending-note">AI 분석이 끝난 뒤 상태를 변경할 수 있습니다.</p>
            ) : (
              <div className="status-option-group">
                {MANUAL_STATUS_OPTIONS.map((status) => (
                  <button
                    key={status}
                    type="button"
                    className={`status-option${item.status === status ? ' is-current' : ''}`}
                    disabled={item.status === status || updatingStatus !== null}
                    aria-busy={updatingStatus === status}
                    onClick={() => handleStatusChange(status)}
                  >
                    {LOST_ITEM_STATUS_LABEL[status]}
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
