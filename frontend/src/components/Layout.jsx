import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `block rounded-md px-3 py-2 text-sm font-medium ${
          isActive ? 'bg-amber-100 text-amber-900' : 'text-slate-700 hover:bg-slate-100'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-lg font-semibold text-slate-900">
            Bakery Inventory
          </Link>
          <div className="flex items-center gap-3">
            <div className="text-sm text-slate-700">
              {user?.username} ({user?.role})
            </div>
            <button
              type="button"
              className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-6 grid grid-cols-12 gap-6">
        <aside className="col-span-12 md:col-span-3">
          <nav className="rounded-lg border bg-white p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 px-3 py-2">
              Navigation
            </div>
            <div className="space-y-1">
              <NavItem to="/">Dashboard</NavItem>
              <NavItem to="/inventory">Inventory</NavItem>
            </div>
          </nav>
        </aside>

        <main className="col-span-12 md:col-span-9">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
