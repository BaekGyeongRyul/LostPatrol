import { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { ShieldCheck, FlaskConical } from 'lucide-react'
import { NAV_ITEMS } from './navItems'
import RobotStatusPill from '../RobotStatusPill'
import { useRobotStatus } from '../../hooks/useRobotStatus'
import { isDemoMode } from '../../lib/api'
import { formatClockTime } from '../../lib/time'

// 다크 사이드바 대신 현대자동차 사이트형 상단 글로벌 헤더.
// 모바일에서는 내비게이션 링크를 숨기고 하단 BottomNav가 그 역할을 대신한다.
export default function Header() {
  const [now, setNow] = useState(() => new Date())
  const { status, offline, loading } = useRobotStatus()

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link to="/" className="site-header__brand">
          <span className="site-header__brand-icon">
            <ShieldCheck size={18} strokeWidth={2.4} />
          </span>
          <span className="site-header__brand-name">LostPatrol</span>
        </Link>

        <nav className="site-header__nav">
          {NAV_ITEMS.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `site-header__link${isActive ? ' is-active' : ''}`}
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="site-header__meta">
          {isDemoMode && (
            <span className="demo-chip" title="Supabase 환경변수가 설정되지 않아 데모 데이터로 표시 중입니다.">
              <FlaskConical size={12} />
              <span>DEMO MODE</span>
            </span>
          )}
          <span className="site-header__clock">{formatClockTime(now)}</span>
          <RobotStatusPill status={status} offline={offline} loading={loading} />
        </div>
      </div>
    </header>
  )
}
