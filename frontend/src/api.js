const base = ''

async function get(path) {
  const r = await fetch(base + path)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}

export const api = {
  meta: () => get('/api/meta'),
  days: () => get('/api/days'),
  summary: () => get('/api/summary'),
  dayAhead: (date, cutoff) => get(`/api/day-ahead?date=${date}&cutoff=${encodeURIComponent(cutoff)}`),
  evolution: (startTime) => get(`/api/evolution?start_time=${encodeURIComponent(startTime)}`),
  accuracyDaily: (cutoff) => get(`/api/accuracy/daily?cutoff=${encodeURIComponent(cutoff)}`),
  distribution: () => get('/api/accuracy/distribution'),
}
