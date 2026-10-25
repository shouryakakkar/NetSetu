import { useLocation } from 'react-router-dom'
import { Bell, Activity } from 'lucide-react'
import useStore from '../../store/useStore'

const PAGE_META = {
  '/dashboard':   { title: 'Security Dashboard',     sub: 'Enterprise security posture and posture metrics' },
  '/upload':      { title: 'Upload & Parse Config',   sub: 'Ingest and sanitize network device configurations' },
  '/compliance':  { title: 'Compliance Audit',       sub: 'Evaluate policies against CIS, NIST, and STIG benchmarks' },
  '/remediation': { title: 'Remediation Runbook',    sub: 'Synthesized CLI commands for non-compliant controls' },
  '/training':    { title: 'AI Heuristic Loop',      sub: 'Zero-shot classification and active learning rules' },
}

export default function Topbar() {
  const location = useLocation()
  const jobs = useStore((s) => s.jobs)
  const meta = Object.entries(PAGE_META).find(([k]) => location.pathname.startsWith(k))?.[1]
    || { title: 'NetSetu', sub: 'Vendor-Agnostic Network Hardening & Compliance' }

  const activeJobs = jobs.filter((j) => j.status === 'processing' || j.status === 'pending').length

  return (
    <header className="topbar">
      <div style={{ flex: 1 }}>
        <div className="topbar-title">{meta.title}</div>
        {meta.sub && <div className="topbar-subtitle">{meta.sub}</div>}
      </div>

      {/* Active telemetry indicator */}
      {activeJobs > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'var(--status-warn-bg)', border: '1px solid var(--status-warn-border)',
          borderRadius: 'var(--radius-sm)', padding: '3px 10px', fontSize: 11.5, color: 'var(--status-warn-txt)',
          fontWeight: 600,
        }}>
          <div className="spinner" style={{ width: 10, height: 10, borderTopColor: 'var(--status-warn-txt)' }} />
          <span>{activeJobs} pipeline task{activeJobs > 1 ? 's' : ''} running</span>
        </div>
      )}

      <button className="btn btn-ghost btn-sm" style={{ padding: '6px', color: 'var(--text-secondary)' }} title="Notifications">
        <Bell size={15} />
      </button>
    </header>
  )
}
