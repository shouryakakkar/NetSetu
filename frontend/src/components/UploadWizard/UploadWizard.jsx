import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { Upload, CheckCircle2, FileText, Cpu, Shield, ArrowRight, ArrowLeft } from 'lucide-react'
import { uploadApi, complianceApi } from '../../api/client'
import useStore from '../../store/useStore'

const STEPS = ['Upload File', 'Confirm Extraction', 'Select Framework', 'Audit Evaluation']

const FRAMEWORKS = [
  { id: 'cis',  label: 'CIS Benchmark Level 1 & 2', sub: 'Center for Internet Security hardening guidelines' },
  { id: 'nist', label: 'NIST SP 800-53 Rev 5',      sub: 'Security and Privacy Controls for Federal Systems' },
  { id: 'stig', label: 'DoD DISA STIG',             sub: 'Department of Defense Security Technical Implementation Guide' },
]

export default function UploadWizard() {
  const navigate = useNavigate()
  const setSelectedJobId = useStore((s) => s.setSelectedJobId)
  const setComplianceResults = useStore((s) => s.setComplianceResults)

  const [step, setStep] = useState(0)
  const [file, setFile] = useState(null)
  const [uploadResult, setUploadResult] = useState(null)
  const [framework, setFramework] = useState('cis')
  const [loading, setLoading] = useState(false)
  const [jobStatus, setJobStatus] = useState(null)

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) setFile(accepted[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/plain': ['.txt', '.cfg', '.conf', '.log'] },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
  })

  const handleUpload = async () => {
    if (!file) return toast.error('Please select a network configuration file first.')
    setLoading(true)
    try {
      const { data } = await uploadApi.uploadConfig(file)
      setUploadResult(data)
      toast.success(`Config parsed! Detected OS: ${data.detected_vendor}`)
      setStep(1)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload and sanitization failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleRunCompliance = async () => {
    setLoading(true)
    setStep(3)
    try {
      // Poll job until normalized
      let job = null
      for (let i = 0; i < 30; i++) {
        const { data } = await uploadApi.getJob(uploadResult.job_id)
        job = data
        setJobStatus(data.status)
        if (['normalized', 'review_required', 'completed'].includes(data.status)) break
        if (data.status === 'failed') {
          toast.error('Normalization error: ' + data.error_message)
          return
        }
        await new Promise((r) => setTimeout(r, 2000))
      }

      // Run compliance check
      const { data: compData } = await complianceApi.runCheck(uploadResult.job_id, framework)
      setComplianceResults(compData)
      setSelectedJobId(uploadResult.job_id)
      toast.success(`Compliance check complete. Score: ${compData.score.toFixed(1)}%`)
      navigate('/compliance')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Compliance evaluation failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fade-in" style={{ maxWidth: 740, margin: '0 auto' }}>
      {/* Wizard Step Progression */}
      <div className="wizard-steps" style={{ marginBottom: 28 }}>
        {STEPS.map((label, i) => (
          <div key={i} className={`wizard-step ${i < step ? 'done' : i === step ? 'active' : ''}`}>
            <div className="step-circle">{i < step ? '✓' : i + 1}</div>
            <span className="step-label">{label}</span>
          </div>
        ))}
      </div>

      {/* Step 0: Upload & Dropzone */}
      {step === 0 && (
        <div className="fade-in">
          <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
            <input {...getInputProps()} />
            <div className="dropzone-icon">
              <Upload size={36} />
            </div>
            <div className="dropzone-title">
              {file ? file.name : 'Select or drag & drop configuration file'}
            </div>
            <div className="dropzone-sub">
              {file
                ? `${(file.size / 1024).toFixed(1)} KB — click to replace`
                : 'Supports .cfg, .txt, .conf (Cisco IOS/NXOS, Junos, PAN-OS, SONiC)'}
            </div>
          </div>

          {file && (
            <div className="card" style={{ marginTop: 14, padding: '12px 16px' }}>
              <div className="flex items-center gap-3">
                <FileText size={18} style={{ color: 'var(--accent-primary)' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{file.name}</div>
                  <div className="text-secondary text-xs">{(file.size / 1024).toFixed(1)} KB</div>
                </div>
                <span className="badge badge-pass">Ready for Ingest</span>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
            <button className="btn btn-primary btn-lg" onClick={handleUpload} disabled={!file || loading}>
              {loading ? (
                <><div className="spinner" /> Uploading & Sanitizing...</>
              ) : (
                <><Upload size={14} /> Upload & Sanitize Config</>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 1: Confirm Extraction & Sanitization Results */}
      {step === 1 && uploadResult && (
        <div className="fade-in">
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title" style={{ marginBottom: 14 }}>Sanitization & Vendor Extraction Summary</div>
            <div className="grid-2" style={{ gap: 12 }}>
              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
                <div className="text-secondary text-xs">Detected Vendor Architecture</div>
                <div style={{ fontWeight: 600, color: 'var(--accent-primary)', fontSize: 15, marginTop: 3, textTransform: 'uppercase' }}>
                  {uploadResult.detected_vendor}
                </div>
              </div>

              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
                <div className="text-secondary text-xs">Secrets & Hashes Redacted</div>
                <div style={{ fontWeight: 600, color: 'var(--status-pass-txt)', fontSize: 15, marginTop: 3 }}>
                  {uploadResult.redacted_secrets} Credentials Sanitized
                </div>
              </div>

              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
                <div className="text-secondary text-xs">Raw Configuration Lines</div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 15, marginTop: 3 }}>
                  {uploadResult.original_lines}
                </div>
              </div>

              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
                <div className="text-secondary text-xs">Normalized Syntax Lines</div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 15, marginTop: 3 }}>
                  {uploadResult.clean_lines}
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 20 }}>
            <button className="btn btn-secondary" onClick={() => setStep(0)}>
              <ArrowLeft size={14} /> Back
            </button>
            <button className="btn btn-primary btn-lg" onClick={() => setStep(2)}>
              <span>Choose Framework</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Framework Selection */}
      {step === 2 && (
        <div className="fade-in">
          <div style={{ marginBottom: 12, color: 'var(--text-secondary)', fontSize: 13, fontWeight: 500 }}>
            Select compliance benchmark standard:
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
            {FRAMEWORKS.map((fw) => {
              const isSelected = framework === fw.id
              return (
                <div
                  key={fw.id}
                  onClick={() => setFramework(fw.id)}
                  className={`card ${isSelected ? 'selected' : ''}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                    cursor: 'pointer',
                    borderColor: isSelected ? 'var(--accent-primary)' : 'var(--border-subtle)',
                    background: isSelected ? '#EFF6FF' : 'var(--bg-surface)',
                    padding: '14px 18px',
                  }}
                >
                  <div style={{
                    width: 34, height: 34, borderRadius: 'var(--radius-sm)',
                    background: isSelected ? '#DBEAFE' : 'var(--bg-base)',
                    border: `1px solid ${isSelected ? '#93C5FD' : 'var(--border-subtle)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: isSelected ? 'var(--accent-primary)' : 'var(--text-secondary)'
                  }}>
                    <Shield size={18} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{fw.label}</div>
                    <div className="text-secondary text-xs">{fw.sub}</div>
                  </div>
                  <div style={{
                    width: 16, height: 16, borderRadius: '50%',
                    border: `1.5px solid ${isSelected ? 'var(--accent-primary)' : '#CBD5E1'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {isSelected && <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-primary)' }} />}
                  </div>
                </div>
              )
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button className="btn btn-secondary" onClick={() => setStep(1)}>
              <ArrowLeft size={14} /> Back
            </button>
            <button className="btn btn-primary btn-lg" onClick={handleRunCompliance} disabled={loading}>
              <CheckCircle2 size={14} /> Execute Compliance Audit
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Processing Status */}
      {step === 3 && (
        <div className="card fade-in" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
            <div className="spinner" style={{ width: 32, height: 32 }} />
          </div>
          <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
            Evaluating Network Security Baseline
          </div>
          <div className="text-secondary text-xs" style={{ marginBottom: 24 }}>
            Executing AST normalization and deterministic policy checks against {framework.toUpperCase()}...
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 300, margin: '0 auto', textAlign: 'left' }}>
            {['Sanitizing and detecting architecture', 'Abstract Syntax Tree (AST) mapping', 'Evaluating compliance controls', 'Synthesizing CLI remediation'].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                <CheckCircle2 size={13} style={{ color: 'var(--status-pass-txt)' }} />
                <span>{s}</span>
              </div>
            ))}
          </div>

          {jobStatus && (
            <div className="alert alert-info" style={{ marginTop: 24, maxWidth: 320, margin: '24px auto 0' }}>
              Current Pipeline Status: <strong>{jobStatus}</strong>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
