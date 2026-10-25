import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Brain, CheckCircle2, XCircle, RefreshCw, Database, Trash2 } from 'lucide-react'
import { aiApi } from '../../api/client'
import useStore from '../../store/useStore'

export default function TrainingGUI() {
  const [pendingItems, setPendingItems] = useState([])
  const [rules, setRules] = useState([])
  const [selectedItem, setSelectedItem] = useState(null)
  const [suggestions, setSuggestions] = useState([])
  const [selectedLabel, setSelectedLabel] = useState('')
  const [customLabel, setCustomLabel] = useState('')
  const [storeAsRegex, setStoreAsRegex] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingSuggest, setLoadingSuggest] = useState(false)
  const [tab, setTab] = useState('pending')  // 'pending' | 'rules'
  const user = useStore((s) => s.user)

  useEffect(() => {
    fetchPending()
    fetchRules()
  }, [])

  const fetchPending = async () => {
    setLoading(true)
    try {
      const { data } = await aiApi.getPending()
      setPendingItems(data.items || [])
    } finally {
      setLoading(false)
    }
  }

  const fetchRules = async () => {
    const { data } = await aiApi.listRules()
    setRules(data || [])
  }

  const handleSelectItem = async (item) => {
    setSelectedItem(item)
    setSelectedLabel('')
    setCustomLabel('')
    setSuggestions([])
    setLoadingSuggest(true)
    try {
      if (item.suggestions?.length > 0) {
        setSuggestions(item.suggestions)
      } else {
        const { data } = await aiApi.suggest(item.raw_line)
        setSuggestions(data || [])
      }
    } catch {
      toast.error('AI model unavailable. Enter mapping manually.')
    } finally {
      setLoadingSuggest(false)
    }
  }

  const handleValidate = async () => {
    const param = customLabel || selectedLabel
    if (!param) return toast.error('Select or enter a parameter mapping.')
    const confidence = suggestions.find((s) => s.label === param)?.score || 1.0
    setLoading(true)
    try {
      await aiApi.validate(selectedItem.raw_line, param, confidence, storeAsRegex)
      toast.success(`Rule saved: "${selectedItem.raw_line}" → ${param}`)
      setPendingItems((prev) => prev.filter((i) => i._id !== selectedItem._id))
      setSelectedItem(null)
      await fetchRules()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save rule.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteRule = async (ruleId) => {
    if (!confirm('Deactivate this mapping rule?')) return
    await aiApi.deleteRule(ruleId)
    toast.success('Mapping rule deactivated.')
    fetchRules()
  }

  return (
    <div className="fade-in">
      {/* Header Tabs & Action Toolbar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, alignItems: 'center' }}>
        {[
          ['pending', Brain, `Pending Review (${pendingItems.length})`],
          ['rules', Database, `Active Rules (${rules.length})`]
        ].map(([id, Icon, label]) => (
          <button
            key={id}
            className={`btn ${tab === id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setTab(id)}
          >
            <Icon size={14} /> {label}
          </button>
        ))}

        <button className="btn btn-secondary btn-sm" style={{ marginLeft: 'auto' }} onClick={() => { fetchPending(); fetchRules() }}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Tab: Pending Review */}
      {tab === 'pending' && (
        <div className="grid-2" style={{ alignItems: 'start', gap: 16 }}>
          {/* Left Column: Review Queue List */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-base)' }}>
              <div className="card-title">Unrecognized Syntax Queue</div>
              <div className="card-subtitle">CLI lines requiring semantic categorization</div>
            </div>

            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
                <div className="spinner" style={{ width: 24, height: 24 }} />
              </div>
            ) : pendingItems.length === 0 ? (
              <div className="empty-state" style={{ padding: '40px 20px' }}>
                <div className="empty-state-icon">
                  <CheckCircle2 size={32} style={{ color: 'var(--status-pass-txt)' }} />
                </div>
                <div className="empty-state-title">No unmapped syntax pending</div>
                <div className="empty-state-sub">All ingested device commands have matched standard AST or heuristic rules.</div>
              </div>
            ) : (
              <div style={{ maxHeight: 520, overflowY: 'auto' }}>
                {pendingItems.map((item) => {
                  const isSelected = selectedItem?._id === item._id
                  return (
                    <div
                      key={item._id}
                      onClick={() => handleSelectItem(item)}
                      style={{
                        padding: '12px 16px',
                        borderBottom: '1px solid var(--border-subtle)',
                        cursor: 'pointer',
                        background: isSelected ? '#EFF6FF' : 'var(--bg-surface)',
                        borderLeft: isSelected ? '3px solid var(--accent-primary)' : '3px solid transparent',
                        transition: 'background var(--transition)',
                      }}
                    >
                      <div className="font-mono text-xs" style={{ color: 'var(--text-primary)', marginBottom: 4 }}>
                        {item.raw_line}
                      </div>
                      {item.suggestions?.length > 0 && (
                        <div className="text-secondary text-xs">
                          AI Match: <strong style={{ color: 'var(--accent-primary)' }}>{item.suggestions[0].label}</strong>
                          {' '}({(item.suggestions[0].score * 100).toFixed(0)}%)
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Right Column: Classification & Rule Formulation Panel */}
          <div className="card">
            {!selectedItem ? (
              <div className="empty-state" style={{ padding: '60px 20px' }}>
                <div className="empty-state-icon">
                  <Brain size={36} />
                </div>
                <div className="empty-state-title">Select a syntax item to inspect</div>
                <div className="empty-state-sub">Choose any flagged command from the queue to evaluate NLP inferences and formulate a rule.</div>
              </div>
            ) : (
              <>
                <div className="card-title" style={{ marginBottom: 4 }}>Map Syntax to Baseline Field</div>
                <div className="card-subtitle" style={{ marginBottom: 12 }}>Define runtime semantic binding into universal schema</div>

                <div className="code-block" style={{ marginBottom: 16 }}>
                  {selectedItem.raw_line}
                </div>

                <div style={{ marginBottom: 16 }}>
                  <div className="form-label" style={{ marginBottom: 8 }}>Zero-Shot NLP Model Inferences</div>
                  {loadingSuggest ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)', fontSize: 12, padding: '12px 0' }}>
                      <div className="spinner" /> Evaluating semantics with BART MNLI...
                    </div>
                  ) : suggestions.length === 0 ? (
                    <div className="alert alert-warn">No confident predictions. Input parameter name manually below.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {suggestions.map((s) => {
                        const isChosen = selectedLabel === s.label
                        return (
                          <div
                            key={s.label}
                            className={`suggestion-card ${isChosen ? 'selected' : ''}`}
                            onClick={() => { setSelectedLabel(s.label); setCustomLabel('') }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span className="font-mono text-xs font-semibold" style={{ color: isChosen ? 'var(--accent-primary)' : 'var(--text-primary)' }}>
                                {s.label}
                              </span>
                              <span className="text-secondary text-xs">{(s.score * 100).toFixed(1)}%</span>
                            </div>
                            <div className="confidence-bar">
                              <div className="confidence-fill" style={{ width: `${s.score * 100}%` }} />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label">Or Specify Parameter Target Manually</label>
                  <input
                    className="form-input"
                    placeholder="e.g. ssh_version or logging_enabled"
                    value={customLabel}
                    onChange={(e) => { setCustomLabel(e.target.value); setSelectedLabel('') }}
                    style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
                  <input
                    type="checkbox"
                    id="regex-check"
                    checked={storeAsRegex}
                    onChange={(e) => setStoreAsRegex(e.target.checked)}
                    style={{ accentColor: 'var(--accent-primary)' }}
                  />
                  <label htmlFor="regex-check" className="text-secondary text-xs" style={{ cursor: 'pointer' }}>
                    Store as exact Regular Expression pattern (not substring match)
                  </label>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className="btn btn-primary"
                    style={{ flex: 1 }}
                    onClick={handleValidate}
                    disabled={loading || (!selectedLabel && !customLabel)}
                  >
                    {loading ? <><div className="spinner" /> Saving Rule...</> : <><CheckCircle2 size={14} /> Commit Mapping Rule</>}
                  </button>
                  <button className="btn btn-secondary" onClick={() => setSelectedItem(null)}>
                    <XCircle size={14} /> Skip
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Tab: Active Rules */}
      {tab === 'rules' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-base)' }}>
            <div className="card-title">Active Heuristic Mapping Rules</div>
            <div className="card-subtitle">Stored in PostgreSQL & applied dynamically during AST normalization</div>
          </div>

          {rules.length === 0 ? (
            <div className="empty-state" style={{ padding: '40px 20px' }}>
              <div className="empty-state-icon">📚</div>
              <div className="empty-state-sub">No custom heuristic rules established yet.</div>
            </div>
          ) : (
            <div className="table-wrapper" style={{ border: 'none', borderRadius: 0 }}>
              <table>
                <thead>
                  <tr>
                    <th>Syntax Pattern</th>
                    <th>Target Parameter</th>
                    <th>Engine Rule Type</th>
                    <th>Model Confidence</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <code style={{ fontSize: 11 }}>{r.raw_pattern}</code>
                      </td>
                      <td>
                        <span className="font-mono text-xs font-semibold" style={{ color: 'var(--accent-primary)' }}>
                          {r.mapped_param}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${r.rule_type === 'regex' ? 'badge-medium' : 'badge-low'}`}>
                          {r.rule_type}
                        </span>
                      </td>
                      <td className="text-secondary text-xs">
                        {(r.confidence * 100).toFixed(0)}%
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDeleteRule(r.id)}
                          style={{ padding: '3px 8px' }}
                        >
                          <Trash2 size={12} /> Deactivate
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
