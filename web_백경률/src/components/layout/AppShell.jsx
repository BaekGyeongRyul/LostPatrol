import { Outlet } from 'react-router-dom'
import Header from './Header'
import BottomNav from './BottomNav'
import Footer from './Footer'

export default function AppShell() {
  return (
    <div className="app-shell">
      <Header />
      <main className="app-shell__content">
        <Outlet />
      </main>
      <Footer />
      <BottomNav />
    </div>
  )
}
