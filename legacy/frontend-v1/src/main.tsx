// ⚠️ DEPRECATED FRONTEND - DO NOT USE ⚠️
console.error(`
╔═══════════════════════════════════════════════════════════════════╗
║  ⚠️  WARNING: YOU ARE RUNNING THE DEPRECATED LEGACY FRONTEND  ⚠️   ║
║                                                                   ║
║  This frontend uses Mapbox (paid) and is OUTDATED.                ║
║  Please stop this and run ./frontend-v2 instead!                  ║
║                                                                   ║
║  cd frontend-v2 && npm run dev                                    ║
╚═══════════════════════════════════════════════════════════════════╝
`);

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import 'mapbox-gl/dist/mapbox-gl.css';
import './index.css'


ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
