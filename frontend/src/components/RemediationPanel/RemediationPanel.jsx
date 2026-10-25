import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Copy, Download, Terminal, Wrench, Check, CheckCircle2 } from 'lucide-react'
import { remediationApi, uploadApi } from '../../api/client'
import useStore from '../../store/useStore'

const SEV_BADGE = {
  CRITICAL: 'badge-critical',
  HIGH: 'badge-high',
  MEDIUM: 'badge-medium',
  LOW: 'badge-low',
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handle = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    toast.success('CLI snippet copied to clipboard.')
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button className="btn btn-secondary btn-sm" onClick={handle} title="Copy CLI Commands" style={{ padding: '3px 8px', fontSize: 11 }}>
      {copied ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
    </button>
  )
}

export default function RemediationPanel() {
  const selectedJobId = useStore((s) => s.selectedJobId)
  const [jobs, setJobs] = useState([])
  const [selectedId, setSelectedId] = useState(selectedJobId || '')
  const [remediation, setRemediation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [filterSev, setFilterSev] = useState('ALL')

  useEffect(() => {
    uploadApi.listJobs().then(({ data }) =>
      setJobs(data.jobs.filter((j) => j.status === 'completed'))
    )
  }, [])

  const load = async (id) => {
    if (!id) return
    setLoading(true)
    try {
      const { data } = await remediationApi.generate(id)
      setRemediation(data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'No compliance scan found. Run a compliance check first.')
    } finally {
      setLoading(false)
    }
  }

  const exportRunbook = () => {
    const items = filtered || []
    const text = items.map((i) =>
      `# ${i.control_id} [${i.severity}] — ${i.title}\n${i.cli_commands}\n`
    ).join('\n')
    const blob = new Blob([`# NetSetu Remediation Runbook\n# Vendor: ${remediation?.vendor}\n\n` + text], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `remediation_runbook_${selectedId}.txt`
    a.click()
    toast.success('Runbook text file exported.')
  }

  const filtered = remediation?.items?.filter(
    (i) => filterSev === 'ALL' || i.severity === filterSev
  ) || []

  return (
    <div className="fade-in">
      {/* Target Scan Selection */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="flex items-center gap-4">
          <div style={{ flex: 1 }}>
            <label className="form-label" style={{ marginBottom: 6 }}>Target Audit Scan</label>
            <select
              className="form-input form-select"
              value={selectedId}
              onChange={(e) => { setSelectedId(e.target.value); setRemediation(null) }}
            >
              <option value="">— Select an evaluated scan —</option>
              {jobs.map((j) => (
                <option key={j.job_id} value={j.job_id}>
                  {j.original_filename} [{j.vendor?.toUpperCase()}] — {j.framework?.toUpperCase()} ({new Date(j.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>
          <div style={{ paddingTop: 20 }}>
            <button className="btn btn-primary" onClick={() => load(selectedId)} disabled={!selectedId || loading}>
              {loading ? <><div className="spinner" /> Synthesizing...</> : <><Terminal size={14} /> Generate Fix Runbook</>}
            </button>
          </div>
        </div>
      </div>

      {remediation && (
        <>
          {/* Executive Issue Counts */}
          <div className="stat-grid" style={{ marginBottom: 20 }}>
            <div className="stat-card">
              <div className="stat-icon blue">📋</div>
              <div className="stat-value">{remediation.total_issues}</div>
              <div className="stat-label">Total Remediations</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon red">🔴</div>
              <div className="stat-value" style={{ color: 'var(--status-fail-txt)' }}>{remediation.critical_count}</div>
              <div className="stat-label">Critical Hardening Fixes</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon amber">🟠</div>
              <div className="stat-value" style={{ color: 'var(--status-warn-txt)' }}>{remediation.high_count}</div>
              <div className="stat-label">High Priority Fixes</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon purple">💻</div>
              <div className="stat-value" style={{ fontSize: 20, textTransform: 'uppercase' }}>{remediation.vendor?.replace('_', ' ')}</div>
              <div className="stat-label">Target Architecture</div>
            </div>
          </div>

          {/* Filter Bar & Export */}
          <div className="card" style={{ padding: '12px 18px', marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <div className="flex items-center gap-2">
              <span className="text-secondary text-xs font-semibold">Filter Severity:</span>
              <div className="flex gap-1">
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => (
                  <button
                    key={s}
                    className={`btn btn-sm ${filterSev === s ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setFilterSev(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={exportRunbook}>
              <Download size={13} /> Export Clean Runbook (.txt)
            </button>
          </div>

          {/* Remediation Cards (GitHub Light IDE Aesthetic) */}
          {filtered.length === 0 ? (
            <div className="card empty-state" style={{ padding: '40px 20px' }}>
              <div className="empty-state-icon">
                <CheckCircle2 size={32} style={{ color: 'var(--status-pass-txt)' }} />
              </div>
              <div className="empty-state-title">No remediation actions found for this severity filter.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {filtered.map((item, idx) => (
                <div
                  key={`${item.control_id}-${idx}`}
                  className="card"
                  style={{
                    padding: 16,
                    borderLeft: `3px solid ${
                      item.severity === 'CRITICAL' ? 'var(--color-critical)' :
                      item.severity === 'HIGH' ? 'var(--color-high)' :
                      item.severity === 'MEDIUM' ? 'var(--color-medium)' : 'var(--color-low)'
                    }`
                  }}
                >
                  <div className="flex items-center gap-3" style={{ marginBottom: 8 }}>
                    <span className={`badge ${SEV_BADGE[item.severity] || 'badge-low'}`}>{item.severity}</span>
                    <code style={{ fontSize: 11, fontWeight: 600 }}>{item.control_id}</code>
                    <span style={{ fontWeight: 600, fontSize: 13, flex: 1, color: 'var(--text-primary)' }}>{item.title}</span>
                  </div>

                  <div style={{ display: 'flex', gap: 20, marginBottom: 12, fontSize: 12, color: 'var(--text-secondary)' }}>
                    <span>Expected Baseline: <code style={{ color: 'var(--text-primary)' }}>{String(item.expected ?? '—')}</code></span>
                    <span>Current Config: <code style={{ color: 'var(--status-fail-txt)' }}>{String(item.actual ?? '—')}</code></span>
                  </div>

                  {/* Clean Light Code Block */}
                  <div className="code-block-header">
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Terminal size={12} style={{ color: 'var(--accent-primary)' }} />
                      <span>Synthesized CLI Commands</span>
                    </span>
                    <CopyButton text={item.cli_commands} />
                  </div>
                  <div className="code-block">
                    {item.cli_commands}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!loading && !remediation && (
        <div className="empty-state" style={{ paddingTop: 64 }}>
          <div className="empty-state-icon">
            <Wrench size={36} />
          </div>
          <div className="empty-state-title">No remediation plan generated yet</div>
          <div className="empty-state-sub">Select an evaluated scan and click "Generate Fix Runbook" to synthesize vendor-accurate rollback and hardening commands.</div>
        </div>
      )}
    </div>
  )
}
