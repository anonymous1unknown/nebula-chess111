import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1c1545',
            color: '#fff',
            border: '1px solid rgba(124,99,232,0.3)',
            borderRadius: '12px',
          },
          success: { iconTheme: { primary: '#34d399', secondary: '#1c1545' } },
          error:   { iconTheme: { primary: '#f87171', secondary: '#1c1545' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)
