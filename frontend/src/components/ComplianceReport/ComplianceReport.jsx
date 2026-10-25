import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Filter, Download, RefreshCw, ChevronDown, ChevronUp, Terminal, ShieldAlert, CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react'
import { complianceApi, uploadApi, reportApi } from '../../api/client'
import useStore from '../../store/useStore'

const SEV_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 }

const STATUS_CONFIG = {
  PASS: { badge: 'badge-pass', label: 'Pass', icon: CheckCircle2 },
  FAIL: { badge: 'badge-fail', label: 'Fail', icon: XCircle },
  WARN: { badge: 'badge-warn', label: 'Warning', icon: AlertTriangle },
  'N/A': { badge: 'badge-na', label: 'N/A', icon: Info },
}

const SEV_BADGE = {
  CRITICAL: 'badge-critical',
  HIGH: 'badge-high',
  MEDIUM: 'badge-medium',
  LOW: 'badge-low',
}

export default function ComplianceReport() {
  const selectedJobId = useStore((s) => s.selectedJobId)
  const storedResults = useStore((s) => s.complianceResults)
  const setComplianceResults = useStore((s) => s.setComplianceResults)

  const [jobs, setJobs] = useState([])
  const [selectedId, setSelectedId] = useState(selectedJobId || '')
  const [results, setResults] = useState(storedResults)
  const [loading, setLoading] = useState(false)
  const [filterStatus, setFilterStatus] = useState('ALL')
  const [filterSev, setFilterSev] = useState('ALL')
  const [expandedId, setExpandedId] = useState(null)
  const [downloadingPdf, setDownloadingPdf] = useState(false)

  useEffect(() => {
    uploadApi.listJobs().then(({ data }) =>
      setJobs(data.jobs.filter((j) => ['completed', 'normalized', 'review_required'].includes(j.status)))
    )
  }, [])

  const loadResults = async (jobId) => {
    setLoading(true)
    try {
      const { data } = await complianceApi.getResults(jobId)
      setResults(data)
      setComplianceResults(data)
    } catch {
      // Results not ready yet
    } finally {
      setLoading(false)
    }
  }

  const handleJobChange = async (id) => {
    setSelectedId(id)
    setResults(null)
    setExpandedId(null)
    if (id) loadResults(id)
  }

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true)
    try {
      await reportApi.downloadPdf(selectedId)
      toast.success('PDF report exported successfully.')
    } catch {
      toast.error('Failed to generate compliance PDF.')
    } finally {
      setDownloadingPdf(false)
    }
  }

  const findings = (results?.findings || [])
    .filter((f) => filterStatus === 'ALL' || f.status === filterStatus)
    .filter((f) => filterSev === 'ALL' || f.severity === filterSev)
    .sort((a, b) => (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9))

  return (
    <div className="fade-in">
      {/* Target Scan Selector & Action Bar */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="flex items-center gap-4">
          <div style={{ flex: 1 }}>
            <label className="form-label" style={{ marginBottom: 6 }}>Target Device Scan</label>
            <select
              className="form-input form-select"
              value={selectedId}
              onChange={(e) => handleJobChange(e.target.value)}
            >
              <option value="">— Select a normalized network audit scan —</option>
              {jobs.map((j) => (
                <option key={j.job_id} value={j.job_id}>
                  {j.original_filename} [{j.vendor?.toUpperCase()}] — {j.framework?.toUpperCase() || 'CIS'} ({new Date(j.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>

          {results && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', paddingTop: 20 }}>
              <button className="btn btn-secondary" onClick={() => loadResults(selectedId)}>
                <RefreshCw size={13} /> Refresh
              </button>
              <button className="btn btn-primary" onClick={handleDownloadPdf} disabled={downloadingPdf}>
                {downloadingPdf ? <div className="spinner" /> : <Download size={13} />}
                {downloadingPdf ? 'Exporting...' : 'Export PDF Report'}
              </button>
            </div>
          )}
        </div>
      </div>

      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <div className="spinner" style={{ width: 28, height: 28 }} />
        </div>
      )}

      {results && !loading && (
        <>
          {/* Executive Posture Metrics Grid */}
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-icon blue">📊</div>
              <div className="stat-value">{results.score.toFixed(1)}%</div>
              <div className="stat-label">Overall Compliance</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon green">✓</div>
              <div className="stat-value" style={{ color: 'var(--status-pass-txt)' }}>{results.passed}</div>
              <div className="stat-label">Passed Controls</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon red">✕</div>
              <div className="stat-value" style={{ color: 'var(--status-fail-txt)' }}>{results.failed}</div>
              <div className="stat-label">Failed Violations</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon amber">⚠</div>
              <div className="stat-value" style={{ color: 'var(--status-warn-txt)' }}>{results.warned}</div>
              <div className="stat-label">Warnings / Partial</div>
            </div>

            <div className="stat-card">
              <div className="stat-icon purple">—</div>
              <div className="stat-value" style={{ color: 'var(--text-secondary)' }}>{results.not_applicable}</div>
              <div className="stat-label">Not Applicable</div>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="card" style={{ padding: '12px 18px', marginBottom: 14 }}>
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1" style={{ color: 'var(--text-secondary)', fontSize: 12, fontWeight: 500 }}>
                  <Filter size={14} />
                  <span>Status:</span>
                </div>
                <div className="flex gap-1">
                  {['ALL', 'PASS', 'FAIL', 'WARN', 'N/A'].map((st) => (
                    <button
                      key={st}
                      className={`btn btn-sm ${filterStatus === st ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setFilterStatus(st)}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm" style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Severity:</span>
                  <select
                    className="form-input form-select"
                    style={{ padding: '4px 28px 4px 10px', fontSize: 12, height: 30, minWidth: 120 }}
                    value={filterSev}
                    onChange={(e) => setFilterSev(e.target.value)}
                  >
                    {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <span className="text-secondary text-sm">
                  Showing <strong>{findings.length}</strong> of {results.total_controls} controls
                </span>
              </div>
            </div>
          </div>

          {/* Compliance Findings Table (High-Density Linear / Vercel Style) */}
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 120 }}>Control ID</th>
                  <th style={{ width: 100 }}>Severity</th>
                  <th>Control Description</th>
                  <th style={{ width: 90 }}>Status</th>
                  <th style={{ width: 110 }}>Expected</th>
                  <th style={{ width: 110 }}>Actual</th>
                  <th style={{ width: 50, textAlign: 'center' }}></th>
                </tr>
              </thead>
              <tbody>
                {findings.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--text-secondary)' }}>
                      No compliance controls match the selected filters.
                    </td>
                  </tr>
                ) : (
                  findings.map((f) => {
                    const isExpanded = expandedId === f.control_id
                    return (
                      <React.Fragment key={f.control_id}>
                        <tr
                          style={{ cursor: 'pointer', background: isExpanded ? 'var(--bg-hover)' : undefined }}
                          onClick={() => setExpandedId(isExpanded ? null : f.control_id)}
                        >
                          <td>
                            <code style={{ fontSize: 11, fontWeight: 600 }}>{f.control_id}</code>
                          </td>
                          <td>
                            <span className={`badge ${SEV_BADGE[f.severity] || 'badge-low'}`}>
                              {f.severity}
                            </span>
                          </td>
                          <td style={{ fontWeight: 500 }}>
                            {f.title}
                          </td>
                          <td>
                            <span className={`badge ${STATUS_CONFIG[f.status]?.badge || 'badge-na'}`}>
                              {f.status}
                            </span>
                          </td>
                          <td>
                            <span className="font-mono text-xs text-secondary">
                              {String(f.expected ?? '—')}
                            </span>
                          </td>
                          <td>
                            <span className="font-mono text-xs text-secondary">
                              {String(f.actual ?? '—')}
                            </span>
                          </td>
                          <td style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </td>
                        </tr>

                        {/* Expandable Remediation Drawer */}
                        {isExpanded && (
                          <tr key={`${f.control_id}-expanded`}>
                            <td colSpan={7} style={{ padding: '0 14px 14px', background: 'var(--bg-base)' }}>
                              <div className="finding-detail-panel">
                                <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 12 }}>
                                  {f.description}
                                </div>

                                {f.status !== 'PASS' && (
                                  <div>
                                    <div className="flex items-center gap-2 mb-2">
                                      <Terminal size={14} style={{ color: 'var(--accent-primary)' }} />
                                      <span className="form-label" style={{ fontWeight: 600 }}>Remediation CLI Guidance</span>
                                    </div>
                                    <div className="code-block">
                                      {f.remediation_hint || '# No specific automated remediation command provided.'}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!loading && !results && !selectedId && (
        <div className="empty-state" style={{ paddingTop: 64 }}>
          <div className="empty-state-icon">
            <ShieldAlert size={38} />
          </div>
          <div className="empty-state-title">Select a scan job to inspect compliance findings</div>
          <div className="empty-state-sub">Choose any completed device scan from the dropdown above to audit CIS, NIST, and STIG policy controls.</div>
        </div>
      )}
    </div>
  )
}
