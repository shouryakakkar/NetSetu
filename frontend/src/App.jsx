import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useEffect } from 'react'
import useStore from './store/useStore'
import LoginPage from './components/Auth/LoginPage'
import Sidebar from './components/Layout/Sidebar'
import Topbar from './components/Layout/Topbar'
import Dashboard from './components/Dashboard/Dashboard'
import UploadWizard from './components/UploadWizard/UploadWizard'
import TrainingGUI from './components/TrainingGUI/TrainingGUI'
import ComplianceReport from './components/ComplianceReport/ComplianceReport'
import RemediationPanel from './components/RemediationPanel/RemediationPanel'

function ProtectedLayout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        <Topbar />
        <div className="page-content">
          <Routes>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="upload" element={<UploadWizard />} />
            <Route path="compliance" element={<ComplianceReport />} />
            <Route path="remediation" element={<RemediationPanel />} />
            <Route path="training" element={<TrainingGUI />} />
          </Routes>
        </div>
      </div>
    </div>
  )
}

function RequireAuth({ children }) {
  const isAuthenticated = useStore((s) => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const fetchCurrentUser = useStore((s) => s.fetchCurrentUser)
  const fetchJobs = useStore((s) => s.fetchJobs)
  const isAuthenticated = useStore((s) => s.isAuthenticated)

  useEffect(() => {
    if (isAuthenticated) {
      fetchCurrentUser()
      fetchJobs()
      const interval = setInterval(fetchJobs, 4000)
      return () => clearInterval(interval)
    }
  }, [isAuthenticated])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <RequireAuth>
              <ProtectedLayout />
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
