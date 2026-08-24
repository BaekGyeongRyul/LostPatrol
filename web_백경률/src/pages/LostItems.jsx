import { useMemo, useState } from 'react'
import { Search, PackageSearch } from 'lucide-react'
import LostItemCard from '../components/LostItemCard'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import PageHeader from '../components/PageHeader'
import { SkeletonCard } from '../components/LoadingState'
import { useLostItems } from '../hooks/useLostItems'
import { LOST_ITEM_STATUS_FILTERS, ITEM_TYPE_FILTERS, formatItemType } from '../lib/statusMap'

export default function LostItems() {
  const { items, loading, error, refetch } = useLostItems()
  const [statusFilter, setStatusFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [query, setQuery] = useState('')

  const filteredItems = useMemo(() => {
    const q = query.trim().toLowerCase()
    return items.filter((item) => {
      if (statusFilter !== 'all' && item.status !== statusFilter) return false
      if (typeFilter !== 'all' && item.item_type !== typeFilter) return false
      if (q) {
        const haystack = `${formatItemType(item.item_type)} ${item.description ?? ''} ${item.location ?? ''}`.toLowerCase()
        if (!haystack.includes(q)) return false
      }
      return true
    })
  }, [items, statusFilter, typeFilter, query])

  return (
    <div className="page">
      <PageHeader title="Lost Items" subtitle="발견된 분실물 조회 및 상태 관리" />

      <section className="panel">
        <div className="panel__header">
          <h2>검색 및 필터</h2>
          <span className="panel__count">{filteredItems.length}건</span>
        </div>

        <div className="filter-bar">
          <div className="filter-bar__search">
            <Search size={16} />
            <input
              type="text"
              placeholder="종류, 설명, 위치로 검색"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          <div className="filter-bar__chips">
            {LOST_ITEM_STATUS_FILTERS.map((filter) => (
              <button
                key={filter.value}
                type="button"
                className={`chip${statusFilter === filter.value ? ' is-active' : ''}`}
                onClick={() => setStatusFilter(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>

          <select
            className="filter-bar__select"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            {ITEM_TYPE_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {loading && (
          <div className="item-grid">
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {!loading && error && <ErrorState onRetry={refetch} />}

        {!loading && !error && filteredItems.length === 0 && (
          <EmptyState
            icon={PackageSearch}
            title="조건에 맞는 분실물이 없습니다"
            description="필터를 조정하거나 검색어를 변경해 보세요."
          />
        )}

        {!loading && !error && filteredItems.length > 0 && (
          <div className="item-grid">
            {filteredItems.map((item) => (
              <LostItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
