import { Link } from 'react-router-dom'
import {
  PackageSearch,
  AlertCircle,
  Archive,
  CheckCircle2,
  ArrowRight,
  Activity,
  Bot,
  ScanSearch,
  Database,
  Monitor,
} from 'lucide-react'
import StatCard from '../components/StatCard'
import LostItemCard from '../components/LostItemCard'
import EmptyState from '../components/EmptyState'
import ErrorState from '../components/ErrorState'
import { SkeletonCard } from '../components/LoadingState'
import { useLostItems } from '../hooks/useLostItems'
import { useRobotCommands } from '../hooks/useRobotCommands'
import { useSafetyStatus } from '../hooks/useSafetyStatus'
import { LOST_ITEM_STATUS } from '../lib/statusMap'
import { formatRelativeTime } from '../lib/time'

const COMMAND_LABEL = {
  forward: '전진 (Forward)',
  backward: '후진 (Backward)',
  left: '좌회전 (Left)',
  right: '우회전 (Right)',
  stop: '정지 (Stop)',
  capture: '촬영 (Capture)',
  patrol_start: '자동순찰 시작 (Patrol Start)',
  patrol_stop: '자동순찰 종료 (Patrol Stop)',
}

// Desktop 한 줄(4칸) 기준 — 실제 분실물이 이보다 적으면 남는 자리를 안내 카드로 채운다.
const RECENT_ITEMS_ROW_TARGET = 4

// 실제 Lost Item이 아닌 단순 UI placeholder. 클릭/Supabase 데이터/상태 변경 없음.
function LostItemPlaceholderCard() {
  return (
    <div className="item-card item-card--placeholder" aria-hidden="true">
      <div className="item-card__photo item-card__photo--placeholder">
        <PackageSearch size={26} strokeWidth={1.6} />
      </div>
      <div className="item-card__body item-card__body--placeholder">
        <p className="item-card--placeholder__title">등록된 분실물이 표시됩니다</p>
        <p className="item-card--placeholder__caption">AI가 탐지한 분실물이 자동으로 등록됩니다.</p>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { items, loading, error, refetch } = useLostItems()
  const { commands } = useRobotCommands({ limit: 6 })
  const { safety } = useSafetyStatus()

  const stats = {
    total: items.length,
    needsReview: items.filter((i) => i.status === LOST_ITEM_STATUS.NEW).length,
    inStorage: items.filter((i) => i.status === LOST_ITEM_STATUS.CONFIRMED).length,
    resolved: items.filter((i) => i.status === LOST_ITEM_STATUS.RESOLVED).length,
  }

  const recentItems = items.slice(0, 6)
  const placeholderCount = Math.max(0, RECENT_ITEMS_ROW_TARGET - recentItems.length)

  return (
    <>
      <section className="dashboard-hero">
        <div className="dashboard-hero__decor" aria-hidden="true">
          <span className="hero-radar-ring" />
          <span className="hero-radar-ring hero-radar-ring--1" />
          <span className="hero-radar-ring hero-radar-ring--2" />
          <span className="hero-radar-core">
            <Bot size={44} strokeWidth={1.6} />
          </span>
        </div>
        <div className="dashboard-hero__inner">
          <div className="dashboard-hero__text">
            <p className="dashboard-hero__eyebrow">AI Patrol Robot Platform</p>
            <h1 className="dashboard-hero__title">LostPatrol</h1>
            <p className="dashboard-hero__subtitle">
              공공장소 AI 분실물 탐색 · 자동 등록 · 안전 순찰 로봇. 로봇이 현장을 순찰하는 동안
              분실물 후보와 안전 이상 징후를 자동으로 기록하고, 관리자는 이 화면에서 모든 것을
              확인합니다.
            </p>
            <div className="dashboard-hero__actions">
              <Link to="/robot-control" className="btn btn--primary btn--lg">
                Robot Control로 이동
              </Link>
              <Link to="/live-patrol" className="btn btn--outline btn--lg">
                실시간 순찰 보기
              </Link>
            </div>
          </div>
        </div>
      </section>

      <div className="page">
        <section className="flow-section">
          <div className="flow-section__header">
            <h2>AI 순찰 프로세스</h2>
            <p>로봇 순찰부터 웹 관제까지, LostPatrol이 자동으로 처리하는 4단계입니다.</p>
          </div>
          <div className="flow-grid">
            <div className="flow-card">
              <span className="flow-card__icon">
                <Bot size={20} strokeWidth={1.8} />
              </span>
              <p className="flow-card__label">
                <span className="flow-card__num">1</span>순찰
              </p>
              <p className="flow-card__caption">Razbot 자동 순찰</p>
            </div>
            <div className="flow-card">
              <span className="flow-card__icon">
                <ScanSearch size={20} strokeWidth={1.8} />
              </span>
              <p className="flow-card__label">
                <span className="flow-card__num">2</span>AI 탐지
              </p>
              <p className="flow-card__caption">카메라로 분실물 탐지</p>
            </div>
            <div className="flow-card">
              <span className="flow-card__icon">
                <Database size={20} strokeWidth={1.8} />
              </span>
              <p className="flow-card__label">
                <span className="flow-card__num">3</span>데이터 등록
              </p>
              <p className="flow-card__caption">Supabase 자동 저장</p>
            </div>
            <div className="flow-card">
              <span className="flow-card__icon">
                <Monitor size={20} strokeWidth={1.8} />
              </span>
              <p className="flow-card__label">
                <span className="flow-card__num">4</span>웹 관제
              </p>
              <p className="flow-card__caption">실시간 확인·제어</p>
            </div>
          </div>
        </section>

        <section className="stat-grid">
          <StatCard icon={PackageSearch} label="전체 발견 분실물" value={stats.total} tone="neutral" />
          <StatCard icon={AlertCircle} label="확인 필요" value={stats.needsReview} tone="amber" />
          <StatCard icon={Archive} label="보관 중" value={stats.inStorage} tone="blue" />
          <StatCard icon={CheckCircle2} label="반환 완료" value={stats.resolved} tone="green" />
        </section>

        <div className="dashboard-grid">
          <section className="panel">
            <div className="panel__header">
              <h2>최근 발견된 분실물</h2>
              <Link to="/lost-items" className="panel__link">
                전체 보기 <ArrowRight size={14} />
              </Link>
            </div>

            {loading && (
              <div className="item-grid">
                {Array.from({ length: 4 }).map((_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            )}

            {!loading && error && <ErrorState onRetry={refetch} />}

            {!loading && !error && recentItems.length === 0 && (
              <EmptyState
                icon={PackageSearch}
                title="아직 발견된 분실물이 없습니다"
                description="로봇을 순찰시키고 촬영 명령을 내리면 이곳에 표시됩니다."
              />
            )}

            {!loading && !error && recentItems.length > 0 && (
              <div className="item-grid">
                {recentItems.map((item) => (
                  <LostItemCard key={item.id} item={item} />
                ))}
                {Array.from({ length: placeholderCount }).map((_, i) => (
                  <LostItemPlaceholderCard key={`placeholder-${i}`} />
                ))}
              </div>
            )}
          </section>

          <section className="panel panel--activity">
            <div className="panel__header">
              <h2>
                <Activity size={16} /> Robot Activity
              </h2>
            </div>
            {commands.length === 0 ? (
              <EmptyState title="아직 전송된 명령이 없습니다" />
            ) : (
              <ul className="activity-list">
                {commands.map((cmd) => (
                  <li key={cmd.id}>
                    <span className="activity-list__time">{formatRelativeTime(cmd.created_at)}</span>
                    <span className="activity-list__command">{COMMAND_LABEL[cmd.command] ?? cmd.command}</span>
                    <span className={`activity-list__status activity-list__status--${cmd.status}`}>
                      {cmd.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <Link to="/robot-control" className="btn btn--primary btn--block">
              Robot Control로 이동
            </Link>

            <div className="safety-mini">
              <p className="safety-mini__title">Safety</p>
              <div className="safety-mini__row">
                <span>🔥 화재 위험</span>
                <span
                  className={`badge badge--${safety ? (safety.fire.severity === 'normal' ? 'green' : 'red') : 'neutral'}`}
                >
                  {safety ? (safety.fire.severity === 'normal' ? 'Normal' : 'Warning') : '—'}
                </span>
              </div>
              <div className="safety-mini__row">
                <span>👤 움직임 감지</span>
                <span className={`badge badge--${safety?.motion.personDetected ? 'amber' : 'green'}`}>
                  {safety ? (safety.motion.personDetected ? 'Person Detected' : 'No Motion') : '—'}
                </span>
              </div>
              <div className="safety-mini__row">
                <span>🔊 이상 고음량</span>
                <span className={`badge badge--${safety?.sound.level === 'high' ? 'amber' : 'green'}`}>
                  {safety ? (safety.sound.level === 'high' ? 'Loud' : 'Normal') : '—'}
                </span>
              </div>
              <Link to="/live-patrol" className="panel__link safety-mini__link">
                실시간 순찰 보기 <ArrowRight size={14} />
              </Link>
            </div>
          </section>
        </div>
      </div>
    </>
  )
}
