import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from './navItems'

export default function BottomNav() {
  return (
    <nav className="bottom-nav">
      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => `bottom-nav__link${isActive ? ' is-active' : ''}`}
        >
          <Icon size={20} strokeWidth={2} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
