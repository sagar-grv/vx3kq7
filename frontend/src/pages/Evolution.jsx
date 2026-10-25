import React, { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ReferenceLine,
} from 'recharts'
import { api } from '../api.js'
import StatCard from '../components/StatCard.jsx'

const HOURS = Array.from({ length: 24 }, (_, h) => String(h).padStart(2, '0') + ':00')

export default function Evolution() {
  const [days, setDays] = useState([])
  const [date, setDate] = useState('')
  const [hour, setHour] = useState('18:00')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.days().then((d) => { setDays(d.days); setDate(d.days[Math.min(14, d.days.length - 1)]) })
  }, [])

  const startTime = date ? `${date}T${hour}:00Z` : ''
  useEffect(() => {
    if (!startTime) return
    setErr(null)
    api.evolution(startTime).then(setData).catch((e) => { setData(null); setErr(String(e)) })
  }, [startTime])

  const rows = useMemo(() => {
    if (!data) return []
    return data.versions.map((v) => ({
      ...v,
      label: v.publish_time.slice(5, 16).replace('T', ' '),
      actual: data.actual,
    }))
  }, [data])

  const firstErr = data && data.versions.length ? data.versions[0].error : null
  const lastErr = data && data.versions.length ? data.versions[data.versions.length - 1].error : null

  return (
    <section>
      <div className="panel controls">
        <h2>Forecast evolution</h2>
        <p className="explainer">
          Every forecast version Elexon published for one delivery hour, in publish order, against the final actual.
          Shows how forecast error shrinks as delivery approaches - evidence for anchoring decisions to the latest version at the cutoff.
        </p>
        <div className="control-row">
          <label>
            Delivery day (UTC)
            <select value={date} onChange={(e) => setDate(e.target.value)}>
              {days.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <label>
            Hour
            <select value={hour} onChange={(e) => setHour(e.target.value)}>
              {HOURS.map((h) => <option key={h} value={h}>{h}</option>)}
            </select>
          </label>
        </div>
      </div>
      {err && <div className="panel error">{err}</div>}
      {data && (
        <>
          <div className="stats">
            <StatCard label="Actual generation" value={data.actual != null ? data.actual.toLocaleString() + ' MW' : '-'} />
            <StatCard label="Forecast versions" value={data.versions.length} />
            <StatCard label="Earliest error" value={firstErr != null ? (firstErr > 0 ? '+' : '') + firstErr.toLocaleString() + ' MW' : '-'} hint={`horizon ${data.versions[0]?.horizon_h} h`} />
            <StatCard label="Latest error" value={lastErr != null ? (lastErr > 0 ? '+' : '') + lastErr.toLocaleString() + ' MW' : '-'} hint={`horizon ${data.versions[data.versions.length - 1]?.horizon_h} h`} />
          </div>
          <div className="panel">
            <ResponsiveContainer width="100%" height={380}>
              <ComposedChart data={rows} margin={{ top: 10, right: 24, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3550" />
                <XAxis dataKey="label" stroke="#8fa1c4" angle={-35} textAnchor="end" height={70} interval={0} tick={{ fontSize: 11 }} />
                <YAxis stroke="#8fa1c4" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} domain={['auto', 'auto']} />
                <Tooltip formatter={(v, name) => [name === 'Actual' ? `${Number(v).toLocaleString()} MW` : `${Number(v).toLocaleString()} MW`, name]} />
                <Legend />
                <Line isAnimationActive={false} type="monotone" dataKey="generation" name="Forecast at publish time" stroke="#60a5fa" strokeWidth={2.5} dot={{ r: 3 }} />
                <Line isAnimationActive={false} type="monotone" dataKey="actual" name="Actual" stroke="#34d399" strokeWidth={2} strokeDasharray="6 3" dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="panel">
            <h3>Version detail</h3>
            <div className="tablewrap">
              <table>
                <thead><tr><th>Published (UTC)</th><th>Horizon</th><th>Forecast MW</th><th>Error MW</th></tr></thead>
                <tbody>
                  {data.versions.map((v) => (
                    <tr key={v.publish_time}>
                      <td>{v.publish_time.slice(0, 16).replace('T', ' ')}</td>
                      <td>{v.horizon_h} h</td>
                      <td>{v.generation.toLocaleString()}</td>
                      <td>{v.error != null ? (v.error > 0 ? '+' : '') + v.error.toLocaleString() : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  )
}
