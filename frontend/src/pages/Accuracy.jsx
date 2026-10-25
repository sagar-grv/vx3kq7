import React, { useEffect, useState } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ReferenceLine,
} from 'recharts'
import { api } from '../api.js'
import StatCard from '../components/StatCard.jsx'

export default function Accuracy() {
  const [summary, setSummary] = useState(null)
  const [daily, setDaily] = useState(null)
  const [dist, setDist] = useState(null)

  useEffect(() => { api.summary().then(setSummary) }, [])
  useEffect(() => { api.accuracyDaily('23:00').then(setDaily) }, [])
  useEffect(() => { api.distribution().then(setDist) }, [])

  return (
    <section>
      <div className="panel controls">
        <h2>Forecast accuracy - quantified</h2>
        <p className="explainer">
          Every January 2026 forecast version scored against the final actual, by forecast horizon.
          Error = forecast - actual (positive = over-forecast). This page is a retrospective full-month analysis - calibration insight, not data available at decision time. The Day-Ahead Desk band uses only the prior 14 days.
        </p>
      </div>
      {summary && (
        <div className="stats">
          <StatCard label="Overall MAE" value={summary.overall.mae + ' MW'} hint={`${summary.overall.n.toLocaleString()} forecast versions`} />
          <StatCard label="Overall RMSE" value={summary.overall.rmse + ' MW'} />
          <StatCard label="Bias" value={(summary.overall.bias > 0 ? '+' : '') + summary.overall.bias + ' MW'} hint="positive = systematic over-forecast" />
          <StatCard label="Overall MAPE" value={summary.overall.mape + '%'} hint="mean |error|/actual per hour" />
          <StatCard label="Overall nMAE (WAPE)" value={summary.overall.nmae + '%'} hint="MAE / mean actual" />
        </div>
      )}
      {summary && summary.decision_set && (
        <div className="panel">
          <h3>Day-ahead decision set - the forecast a desk would actually have used</h3>
          <p className="explainer">{summary.decision_set.description}</p>
          <div className="stats">
            <StatCard label="Decision-set MAE" value={summary.decision_set.mae + ' MW'} hint={`${summary.decision_set.n} delivery hours`} />
            <StatCard label="Decision-set RMSE" value={summary.decision_set.rmse + ' MW'} />
            <StatCard label="Decision-set bias" value={(summary.decision_set.bias > 0 ? '+' : '') + summary.decision_set.bias + ' MW'} />
            <StatCard label="Decision-set MAPE" value={summary.decision_set.mape + '%'} />
          </div>
        </div>
      )}
      <div className="grid2">
        {summary && (
          <div className="panel">
            <h3>Error by forecast horizon</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={summary.by_horizon} margin={{ top: 10, right: 24, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3550" />
                <XAxis dataKey="bucket" stroke="#8fa1c4" />
                <YAxis stroke="#8fa1c4" />
                <Tooltip formatter={(v, name) => [`${Number(v).toLocaleString()} MW`, name]} />
                <Legend />
                <Bar isAnimationActive={false} dataKey="mae" name="MAE" fill="#60a5fa" />
                <Bar isAnimationActive={false} dataKey="rmse" name="RMSE" fill="#a78bfa" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        {daily && (
          <div className="panel">
            <h3>Day-ahead MAE by delivery day (cutoff 23:00 D-1)</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={daily.days} margin={{ top: 10, right: 24, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3550" />
                <XAxis dataKey="date" stroke="#8fa1c4" tickFormatter={(d) => d.slice(8)} />
                <YAxis stroke="#8fa1c4" />
                <Tooltip formatter={(v, name) => [name === 'mape' ? v + ' %' : `${Number(v).toLocaleString()} MW`, name]} />
                <Legend />
                <Line isAnimationActive={false} type="monotone" dataKey="mae" name="MAE" stroke="#60a5fa" strokeWidth={2.5} dot={{ r: 2 }} />
                <Line isAnimationActive={false} type="monotone" dataKey="rmse" name="RMSE" stroke="#a78bfa" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
      {dist && (
        <div className="panel">
          <h3>Day-ahead error distribution (forecasts 12-36 h ahead, n={dist.n.toLocaleString()})</h3>
          <p className="explainer">P10 = {dist.p10?.toLocaleString()} MW, P90 = +{dist.p90?.toLocaleString()} MW. 80% of day-ahead hourly forecasts land inside this band.</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={dist.bins.map((b) => ({ ...b, label: `${(b.from / 1000).toFixed(1)}k..${(b.to / 1000).toFixed(1)}k` }))} margin={{ top: 10, right: 24, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3550" />
              <XAxis dataKey="label" stroke="#8fa1c4" tick={{ fontSize: 10 }} interval={1} />
              <YAxis stroke="#8fa1c4" />
              <Tooltip />
              <Bar isAnimationActive={false} dataKey="count" name="Hours" fill="#34d399" />
              <ReferenceLine x={dist.bins.findIndex((b) => 0 >= b.from && 0 < b.to)} stroke="#f87171" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
