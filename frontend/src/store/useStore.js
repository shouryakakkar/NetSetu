import { create } from 'zustand'
import { authApi } from '../api/client'

const useStore = create((set, get) => ({
  // ── Auth ────────────────────────────────────────────────────────────────────
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),

  login: async (username, password) => {
    const { data } = await authApi.login(username, password)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    const meRes = await authApi.me()
    set({ user: meRes.data, isAuthenticated: true })
    return meRes.data
  },

  logout: () => {
    localStorage.clear()
    set({ user: null, isAuthenticated: false })
  },

  fetchCurrentUser: async () => {
    try {
      const { data } = await authApi.me()
      set({ user: data, isAuthenticated: true })
    } catch {
      set({ user: null, isAuthenticated: false })
    }
  },

  // ── Jobs ────────────────────────────────────────────────────────────────────
  jobs: [],
  selectedJobId: null,

  setJobs: (jobs) => set({ jobs }),
  setSelectedJobId: (id) => set({ selectedJobId: id }),
  fetchJobs: async () => {
    try {
      const { uploadApi } = await import('../api/client')
      const { data } = await uploadApi.listJobs()
      set({ jobs: data.jobs || [] })
      return data.jobs || []
    } catch {
      return []
    }
  },

  // ── Compliance Results ──────────────────────────────────────────────────────
  complianceResults: null,
  setComplianceResults: (r) => set({ complianceResults: r }),

  // ── Remediation ─────────────────────────────────────────────────────────────
  remediationData: null,
  setRemediationData: (d) => set({ remediationData: d }),

  // ── AI Pending Review ───────────────────────────────────────────────────────
  pendingItems: [],
  setPendingItems: (items) => set({ pendingItems: items }),

  // ── UI State ────────────────────────────────────────────────────────────────
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  activeView: 'dashboard',
  setActiveView: (view) => set({ activeView: view }),
}))

export default useStore
