import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid
} from 'recharts'
import { Shield, AlertTriangle, CheckCircle, Upload, ArrowUpRight } from 'lucide-react'
import { uploadApi } from '../../api/client'
import useStore from '../../store/useStore'

const STATUS_BADGE_MAP = {
  completed: 'badge-pass',
  normalized: 'badge-low',
  review_required: 'badge-warn',
  failed: 'badge-fail',
  processing: 'badge-medium',
  pending: 'badge-na',
}

function ScoreRing({ score }) {
  const radius = 48
  const stroke = 6
  const circ = 2 * Math.PI * radius
  const offset = circ - (score / 100) * circ
  const color = score >= 80 ? 'var(--color-pass)' : score >= 60 ? 'var(--color-warn)' : 'var(--color-fail)'

  return (
    <div className="score-ring-wrapper">
      <div className="score-ring" style={{ width: 110, height: 110, position: 'relative' }}>
        <svg width="110" height="110">
          <circle cx="55" cy="55" r={radius} fill="none" stroke="#E2E8F0" strokeWidth={stroke} />
          <circle
            cx="55" cy="55" r={radius} fill="none"
            stroke={color} strokeWidth={stroke}
            strokeDasharray={circ} strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.8s ease', transform: 'rotate(-90deg)', transformOrigin: '55px 55px' }}
          />
        </svg>
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center'
        }}>
          <span style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            {score ? score.toFixed(0) : '0'}%
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>Index</span>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const setStoreJobs = useStore((s) => s.setJobs)

  useEffect(() => {
    uploadApi.listJobs().then(({ data }) => {
      setJobs(data.jobs || [])
      setStoreJobs(data.jobs || [])
    }).finally(() => setLoading(false))
  }, [])

  const completed = jobs.filter((j) => j.status === 'completed')
  const avgScore = completed.length
    ? completed.reduce((a, j) => a + (j.compliance_score || 0), 0) / completed.length
    : 0

  const frameworkCounts = jobs.reduce((acc, j) => {
    if (j.framework) acc[j.framework.toUpperCase()] = (acc[j.framework.toUpperCase()] || 0) + 1
    return acc
  }, {})

  const barData = Object.entries(frameworkCounts).map(([name, count]) => ({ name, count }))
  const BAR_COLORS = ['#2563EB', '#059669', '#7C3AED']

  return (
    <div className="fade-in">
      {/* Stat cards */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-icon blue"><Shield size={16} /></div>
          <div className="stat-value">{jobs.length}</div>
          <div className="stat-label">Total Device Scans</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><CheckCircle size={16} /></div>
          <div className="stat-value">{completed.length}</div>
          <div className="stat-label">Evaluated Compliant</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber"><AlertTriangle size={16} /></div>
          <div className="stat-value">{jobs.filter((j) => j.status === 'review_required').length}</div>
          <div className="stat-label">Syntax Needing Review</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon purple">📈</div>
          <div className="stat-value">{avgScore.toFixed(0)}%</div>
          <div className="stat-label">Fleet Compliance Average</div>
        </div>
      </div>

      <div className="grid-2" style={{ gap: 16, marginBottom: 20 }}>
        {/* Posture Ring */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Security Posture Score</div>
              <div className="card-subtitle">Aggregated benchmark across {completed.length} audited configurations</div>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0' }}>
            <ScoreRing score={avgScore} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 32, marginTop: 4 }}>
            {[
              ['Passing Rate', `${completed.length ? ((completed.filter(c => c.compliance_score >= 80).length / completed.length)*100).toFixed(0) : 0}%`, 'var(--status-pass-txt)'],
              ['Vulnerability Rate', `${completed.length ? ((completed.filter(c => c.compliance_score < 60).length / completed.length)*100).toFixed(0) : 0}%`, 'var(--status-fail-txt)'],
            ].map(([label, val, c]) => (
              <div key={label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{label}</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: c }}>{val}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Framework distribution chart */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Framework Utilization</div>
              <div className="card-subtitle">Audits categorized by security standard</div>
            </div>
          </div>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={170}>
              <BarChart data={barData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: 6, fontSize: 12, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}
                  labelStyle={{ color: 'var(--text-primary)', fontWeight: 600 }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {barData.map((_, i) => <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ padding: '24px 20px' }}>
              <div className="empty-state-icon">📊</div>
              <div className="empty-state-sub">No framework audits recorded yet. Upload a network device config to begin.</div>
            </div>
          )}
        </div>
      </div>

      {/* Recent Scans Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div className="card-title">Recent Device Scans</div>
            <div className="card-subtitle">Configuration audit log and real-time processing status</div>
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/upload')}>
            <Upload size={13} /> Upload Config
          </button>
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
            <div className="spinner" style={{ width: 24, height: 24 }} />
          </div>
        ) : jobs.length === 0 ? (
          <div className="empty-state" style={{ padding: '40px 20px' }}>
            <div className="empty-state-icon">📄</div>
            <div className="empty-state-title">No audit records found</div>
            <div className="empty-state-sub">Upload your Cisco, Junos, PAN-OS, or SONiC configurations to begin compliance scoring.</div>
          </div>
        ) : (
          <div className="table-wrapper" style={{ border: 'none', borderRadius: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Configuration File</th>
                  <th>Vendor OS</th>
                  <th>Job Status</th>
                  <th>Framework</th>
                  <th>Compliance Score</th>
                  <th>Date Ingested</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.slice(0, 10).map((job) => (
                  <tr key={job.job_id}>
                    <td>
                      <code style={{ fontSize: 12 }}>{job.original_filename}</code>
                    </td>
                    <td>
                      <span className="text-secondary text-xs font-semibold" style={{ textTransform: 'uppercase' }}>
                        {job.vendor?.replace('_', ' ') || 'UNKNOWN'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${STATUS_BADGE_MAP[job.status] || 'badge-na'}`}>
                        {job.status?.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      <span className="text-secondary text-xs" style={{ textTransform: 'uppercase', fontWeight: 500 }}>
                        {job.framework || '—'}
                      </span>
                    </td>
                    <td>
                      {job.compliance_score != null ? (
                        <span style={{
                          fontWeight: 700,
                          color: job.compliance_score >= 80 ? 'var(--status-pass-txt)' : job.compliance_score >= 60 ? 'var(--status-warn-txt)' : 'var(--status-fail-txt)',
                        }}>
                          {job.compliance_score.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="text-secondary text-xs">
                      {new Date(job.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => {
                          useStore.getState().setSelectedJobId(job.job_id)
                          navigate('/compliance')
                        }}
                      >
                        <span>View Details</span>
                        <ArrowUpRight size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
