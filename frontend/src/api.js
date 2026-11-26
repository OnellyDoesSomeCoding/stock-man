// All calls to our FastAPI backend live here.

const BACKEND_DOWN = "Can't reach the backend. Is it running on port 8000?"

async function request(url, { method = 'GET', signal, json } = {}) {
  let res
  try {
    res = await fetch(url, {
      method,
      signal,
      headers: json ? { 'Content-Type': 'application/json' } : undefined,
      body: json ? JSON.stringify(json) : undefined,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new Error(BACKEND_DOWN)
  }

  if (res.status === 204) return null // success, nothing to send back (e.g. a delete)
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    if (body === null) throw new Error(BACKEND_DOWN) // proxy error: no JSON from FastAPI
    throw new Error(errorMessage(body.detail, res.status))
  }
  return body
}

// FastAPI sends either a sentence, or (for invalid input) a list of problems.
function errorMessage(detail, status) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  return `Request failed (${status})`
}

const stockUrl = (ticker) => `/api/stocks/${encodeURIComponent(ticker)}`
const watchUrl = (ticker) => `/api/watchlist/${encodeURIComponent(ticker)}`

// Only ask for indicators that are wanted (empty sma/rsi would be rejected by the backend).
export function fetchPrices(ticker, range, { sma = [], rsi = null } = {}, signal) {
  const params = new URLSearchParams({ range })
  if (sma.length) params.set('sma', sma.join(','))
  if (rsi) params.set('rsi', rsi)
  return request(`${stockUrl(ticker)}/prices?${params}`, { signal })
}

export const fetchStats = (ticker, signal) => request(`${stockUrl(ticker)}/stats`, { signal })

export const fetchBacktest = (ticker, strategy, range, signal) =>
  request(`${stockUrl(ticker)}/backtest?${new URLSearchParams({ strategy, range })}`, { signal })

export const fetchForecast = (ticker, horizon, range, signal) =>
  request(`${stockUrl(ticker)}/forecast?${new URLSearchParams({ horizon, range })}`, { signal })

export const searchTickers = (query, signal) => request(`/api/search?q=${encodeURIComponent(query)}`, { signal })

export const fetchWatchlist = (signal) => request('/api/watchlist', { signal })
export const addToWatchlist = (ticker) => request(watchUrl(ticker), { method: 'POST' })
export const removeFromWatchlist = (ticker) => request(watchUrl(ticker), { method: 'DELETE' })

export const fetchPortfolio = (signal) => request('/api/portfolio', { signal })
export const placeTrade = (ticker, side, shares) =>
  request('/api/portfolio/trades', { method: 'POST', json: { ticker, side, shares } })
export const resetPortfolio = () => request('/api/portfolio/reset', { method: 'POST' })
