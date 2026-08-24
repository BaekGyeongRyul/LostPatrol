import { Link } from 'react-router-dom'
import {
  PackageSearch,
  AlertCircle,
  Archive,
  CheckCircle2,
  ArrowRight,
  Activity,
  Camera,
  ShieldCheck,
  Radar,
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

  return (
    <>
      <section className="dashboard-hero">
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
          <div className="dashboard-hero__visual" aria-hidden="true">
            <div className="hero-tile hero-tile--a">
              <Camera size={30} strokeWidth={1.7} />
            </div>
            <div className="hero-tile hero-tile--b">
              <ShieldCheck size={30} strokeWidth={1.7} />
            </div>
            <div className="hero-tile hero-tile--c">
              <PackageSearch size={30} strokeWidth={1.7} />
            </div>
            <div className="hero-tile hero-tile--d">
              <Radar size={30} strokeWidth={1.7} />
            </div>
          </div>
        </div>
      </section>

      <div className="page">
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
