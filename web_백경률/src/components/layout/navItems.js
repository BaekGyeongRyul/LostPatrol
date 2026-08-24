import { LayoutDashboard, Gamepad2, PackageSearch, Cctv } from 'lucide-react'

export const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/robot-control', label: 'Robot Control', icon: Gamepad2 },
  { to: '/live-patrol', label: '실시간 순찰', icon: Cctv },
  { to: '/lost-items', label: 'Lost Items', icon: PackageSearch },
]
