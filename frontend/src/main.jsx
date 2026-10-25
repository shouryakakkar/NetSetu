import React from 'react'
import ReactDOM from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
    <Toaster
      position="top-right"
      toastOptions={{
        style: {
          background: '#FFFFFF',
          color: '#0F172A',
          border: '1px solid #E2E8F0',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
          fontFamily: "'Inter', sans-serif",
          fontSize: '12.5px',
          fontWeight: 500,
          borderRadius: '6px',
        },
        success: { iconTheme: { primary: '#059669', secondary: '#FFFFFF' } },
        error:   { iconTheme: { primary: '#DC2626', secondary: '#FFFFFF' } },
      }}
    />
  </React.StrictMode>
)
