import React, { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ReferenceLine,
} from 'recharts'
import { api } from '../api.js'
import StatCard from '../components/StatCard.jsx'

const CUTOFFS = ['12:00', '17:00', '20:00', '23:00']
const fmtGWh = (mwh) => (mwh / 1000).toFixed(1) + ' GWh'

export default function DayAhead() {
  const [days, setDays] = useState([])
  const [date, setDate] = useState('')
  const [cutoff, setCutoff] = useState('23:00')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.days().then((d) => {
      setDays(d.days)
      setDate(d.days[Math.min(14, d.days.length - 1)])
    })
  }, [])

  useEffect(() => {
    if (!date) return
    setErr(null)
    api.dayAhead(date, cutoff).then(setData).catch((e) => { setData(null); setErr(String(e)) })
  }, [date, cutoff])

  const rows = useMemo(() => (data ? data.points.map((p) => ({ ...p, label: p.hour.slice(11, 16) })) : []), [data])

  return (
    <section>
      <div className="panel controls">
        <h2>Day-ahead purchase desk</h2>
        <p className="explainer">
          The wind forecast your desk would actually have seen at the decision cutoff on the day before delivery,
          plotted against what the wind fleet really generated. The dashed band is the empirical P10-P90 error range
          for forecasts at that horizon, calibrated only on the 14 days before the cutoff - no lookahead.
        </p>
        <div className="control-row">
          <label>
            Delivery day (UTC)
            <select value={date} onChange={(e) => setDate(e.target.value)}>
              {days.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <label>
            Decision cutoff (D-1, UTC)
            <select value={cutoff} onChange={(e) => setCutoff(e.target.value)}>
              {CUTOFFS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
        </div>
      </div>
      {err && <div className="panel error">{err}</div>}
      {data && (
        <>
          <div className="stats">
            <StatCard label="Forecast wind energy" value={fmtGWh(data.totals.forecast_mwh)} hint={`cutoff ${data.cutoff_utc}`} />
            <StatCard label="Actual wind energy" value={fmtGWh(data.totals.actual_mwh)} />
            <StatCard
              label="Day-ahead energy error"
              value={(data.totals.energy_error_mwh > 0 ? '+' : '') + fmtGWh(data.totals.energy_error_mwh)}
              hint="positive = over-forecast = over-procurement risk"
            />
            <StatCard label="MAE" value={data.totals.mae + ' MW'} hint={`${data.totals.n} hourly points`} />
            <StatCard label="MAPE" value={data.totals.mape + '%'} hint="mean |error|/actual per hour" />
            <StatCard label="nMAE (WAPE)" value={data.totals.nmae + '%'} hint="MAE / mean actual" />
          </div>
          <div className="panel">
            <ResponsiveContainer width="100%" height={380}>
              <ComposedChart data={rows} margin={{ top: 10, right: 24, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3550" />
                <XAxis dataKey="label" stroke="#8fa1c4" />
                <YAxis stroke="#8fa1c4" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v, name) => [`${Number(v).toLocaleString()} MW`, name]} />
                <Legend />
                <Line isAnimationActive={false} type="monotone" dataKey="actual" name="Actual (FUELHH)" stroke="#34d399" strokeWidth={2.5} dot={false} />
                <Line isAnimationActive={false} type="monotone" dataKey="forecast" name="Latest day-ahead forecast (WINDFOR)" stroke="#60a5fa" strokeWidth={2.5} dot={false} />
                <Line isAnimationActive={false} type="monotone" dataKey="band_high" name="P90 band (prior 14 days)" stroke="#64748b" strokeDasharray="4 4" dot={false} />
                <Line isAnimationActive={false} type="monotone" dataKey="band_low" name="P10 band (prior 14 days)" stroke="#64748b" strokeDasharray="4 4" dot={false} />
                <ReferenceLine y={0} stroke="#2a3550" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="panel">
            <h3>Hourly detail</h3>
            <div className="tablewrap">
              <table>
                <thead>
                  <tr><th>Hour (UTC)</th><th>Actual MW</th><th>Forecast MW</th><th>Published</th><th>Horizon</th><th>Error MW</th></tr>
                </thead>
                <tbody>
                  {data.points.map((p) => (
                    <tr key={p.hour} className={p.error !== null && Math.abs(p.error) > 4000 ? 'bad' : ''}>
                      <td>{p.hour.slice(11, 16)}</td>
                      <td>{p.actual?.toLocaleString() ?? '-'}</td>
                      <td>{p.forecast?.toLocaleString() ?? '-'}</td>
                      <td>{p.publish_time ? p.publish_time.slice(5, 16).replace('T', ' ') : '-'}</td>
                      <td>{p.horizon_h != null ? p.horizon_h + ' h' : '-'}</td>
                      <td>{p.error != null ? (p.error > 0 ? '+' : '') + p.error.toLocaleString() : '-'}</td>
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
