import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Shield } from 'lucide-react'
import useStore from '../../store/useStore'
import { authApi } from '../../api/client'

export default function LoginPage() {
  const [mode, setMode] = useState('login')  // 'login' | 'register'
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const login = useStore((s) => s.login)
  const navigate = useNavigate()

  const handleChange = (e) => {
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      if (mode === 'login') {
        await login(form.username, form.password)
        toast.success('Authenticated successfully.')
        navigate('/dashboard')
      } else {
        await authApi.register({ username: form.username, email: form.email, password: form.password })
        toast.success('Account created. Please log in.')
        setMode('login')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed. Please check credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card fade-in">
        <div className="login-logo">
          <div className="login-logo-icon">
            <Shield size={20} />
          </div>
          <div>
            <div className="login-title">NetSetu</div>
            <div className="login-subtitle">
              {mode === 'login' ? 'Sign in to access network compliance telemetry' : 'Register an administrative security auditor account'}
            </div>
          </div>
        </div>

        {error && (
          <div className="alert alert-error">
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              className="form-input"
              name="username"
              placeholder="e.g. admin or auditor_jane"
              value={form.username}
              onChange={handleChange}
              required
              autoFocus
            />
          </div>

          {mode === 'register' && (
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                className="form-input"
                name="email"
                type="email"
                placeholder="auditor@enterprise.com"
                value={form.email}
                onChange={handleChange}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              className="form-input"
              name="password"
              type="password"
              placeholder="••••••••••••"
              value={form.password}
              onChange={handleChange}
              required
              minLength={8}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary w-full"
            style={{ marginTop: 8, padding: '9px 16px' }}
            disabled={loading}
          >
            {loading ? (
              <><div className="spinner" /> Authenticating...</>
            ) : (
              mode === 'login' ? 'Sign In →' : 'Create Auditor Account →'
            )}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 18 }}>
          <span className="text-secondary text-sm">
            {mode === 'login' ? "Don't have an account? " : 'Already have credentials? '}
          </span>
          <button
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
            className="btn btn-ghost btn-sm"
            style={{ color: 'var(--accent-primary)', padding: '0 4px', fontWeight: 600 }}
          >
            {mode === 'login' ? 'Register' : 'Sign in'}
          </button>
        </div>

        {/* Quiet Minimalist Device Tags */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 24, justifyContent: 'center' }}>
          {['Cisco IOS', 'Junos', 'PAN-OS', 'SONiC', 'CIS Benchmark', 'NIST 800-53', 'DISA STIG'].map((tag) => (
            <span key={tag} style={{
              background: 'var(--bg-hover)', border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)', padding: '2px 7px', fontSize: 11, color: 'var(--text-secondary)',
              fontWeight: 500,
            }}>{tag}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
