import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: inject JWT ──────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor: handle 401 ─────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalReq = err.config
    if (err.response?.status === 401 && !originalReq._retry) {
      originalReq._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          originalReq.headers.Authorization = `Bearer ${data.access_token}`
          return api(originalReq)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (username, password) =>
    api.post('/auth/token', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
}

// ── Upload ────────────────────────────────────────────────────────────────────
export const uploadApi = {
  uploadConfig: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  listJobs: () => api.get('/upload/jobs'),
  getJob: (jobId) => api.get(`/upload/jobs/${jobId}`),
}

// ── Compliance ────────────────────────────────────────────────────────────────
export const complianceApi = {
  runCheck: (jobId, framework) => api.post('/compliance/check', { job_id: jobId, framework }),
  getResults: (jobId) => api.get(`/compliance/${jobId}`),
}

// ── Remediation ───────────────────────────────────────────────────────────────
export const remediationApi = {
  generate: (jobId) => api.post('/remediation/generate', { job_id: jobId }),
}

// ── Reports ───────────────────────────────────────────────────────────────────
export const reportApi = {
  downloadPdf: async (jobId) => {
    const res = await api.get(`/report/pdf/${jobId}`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `compliance_report_${jobId}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  },
}

// ── AI Training ───────────────────────────────────────────────────────────────
export const aiApi = {
  getPending: (limit = 50) => api.get(`/ai/pending?limit=${limit}`),
  suggest: (rawLine) => api.post('/ai/suggest', { raw_line: rawLine }),
  validate: (rawLine, acceptedParam, confidence, storeAsRegex = false) =>
    api.post('/ai/validate', {
      raw_line: rawLine,
      accepted_param: acceptedParam,
      confidence,
      store_as_regex: storeAsRegex,
    }),
  listRules: () => api.get('/ai/rules'),
  deleteRule: (ruleId) => api.delete(`/ai/rules/${ruleId}`),
  seedDemo: () => api.post('/ai/seed-demo'),
}

export default api
