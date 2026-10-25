import { useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Upload, ShieldCheck, Wrench,
  Brain, LogOut, Shield
} from 'lucide-react'
import useStore from '../../store/useStore'

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: 'Dashboard',   path: '/dashboard' },
  { icon: Upload,          label: 'Upload Config', path: '/upload' },
  { icon: ShieldCheck,     label: 'Compliance',   path: '/compliance' },
  { icon: Wrench,          label: 'Remediation',  path: '/remediation' },
]

const ADMIN_NAV = [
  { icon: Brain, label: 'AI Training', path: '/training' },
]

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = useStore((s) => s.user)
  const logout = useStore((s) => s.logout)

  const isActive = (path) => location.pathname.startsWith(path)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Shield size={18} />
        </div>
        <div>
          <div className="sidebar-logo-text">NetSetu</div>
          <div className="sidebar-logo-sub">Security Compliance</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Platform</div>
        {NAV_ITEMS.map(({ icon: Icon, label, path }) => (
          <button
            key={path}
            className={`nav-item ${isActive(path) ? 'active' : ''}`}
            onClick={() => navigate(path)}
          >
            <Icon className="nav-icon" size={16} />
            <span style={{ flex: 1 }}>{label}</span>
          </button>
        ))}

        <div className="nav-section-label" style={{ marginTop: 12 }}>Intelligence</div>
        {ADMIN_NAV.map(({ icon: Icon, label, path }) => (
          <button
            key={path}
            className={`nav-item ${isActive(path) ? 'active' : ''}`}
            onClick={() => navigate(path)}
          >
            <Icon className="nav-icon" size={16} />
            <span style={{ flex: 1 }}>{label}</span>
          </button>
        ))}
      </nav>

      {/* Footer / User Profile */}
      <div className="sidebar-footer">
        <div className="user-chip">
          <div className="user-avatar">
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="user-name truncate">{user?.username || 'Authenticated User'}</div>
            <div className="user-role">{user?.role || 'Auditor'}</div>
          </div>
          <button
            onClick={handleLogout}
            className="btn btn-ghost btn-sm"
            title="Sign out"
            style={{ padding: '4px', minWidth: 0, color: 'var(--text-secondary)' }}
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  )
}
