import React, { useEffect, useState } from 'react'
import { api } from './api.js'
import DayAhead from './pages/DayAhead.jsx'
import Evolution from './pages/Evolution.jsx'
import Accuracy from './pages/Accuracy.jsx'

const TABS = [
  { id: 'desk', label: 'Day-Ahead Desk' },
  { id: 'evolution', label: 'Forecast Evolution' },
  { id: 'accuracy', label: 'Accuracy Analytics' },
]

export default function App() {
  const [tab, setTab] = useState('desk')
  const [meta, setMeta] = useState(null)
  useEffect(() => { api.meta().then(setMeta).catch(() => {}) }, [])
  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>WindSight</h1>
          <p className="subtitle">Day-ahead UK wind forecast intelligence - pilot build (Elexon FUELHH / WINDFOR, delivery days: January 2026)</p>
        </div>
        {meta && (
          <div className="meta">
            <span>{meta.actuals.records.toLocaleString()} actual half-hours</span>
            <span>{meta.forecasts.records.toLocaleString()} forecast versions</span>
          </div>
        )}
      </header>
      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={tab === t.id ? 'tab active' : 'tab'} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>
      <main>
        {tab === 'desk' && <DayAhead />}
        {tab === 'evolution' && <Evolution />}
        {tab === 'accuracy' && <Accuracy />}
      </main>
      <footer className="foot">
        Data: Elexon BMRS Insights (FUELHH actual generation, WINDFOR national wind forecast). All times UTC. MW unless noted.
      </footer>
    </div>
  )
}
