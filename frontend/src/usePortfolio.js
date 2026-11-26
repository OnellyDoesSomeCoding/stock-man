import { useEffect, useState } from 'react'
import { fetchPortfolio, placeTrade, resetPortfolio } from './api'

/**
 * The paper portfolio (fake money), stored by the backend.
 * data: null until the first load finishes.
 * trade() resolves to { ok: true, trade } or { ok: false, error } so the caller can show a message.
 */
export default function usePortfolio() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    fetchPortfolio(ctrl.signal)
      .then(setData)
      .catch((err) => {
        if (err.name !== 'AbortError') setError(err.message)
      })
    return () => ctrl.abort()
  }, [])

  const trade = async (ticker, side, shares) => {
    setBusy(true)
    try {
      const result = await placeTrade(ticker, side, shares)
      setData(result.portfolio)
      return { ok: true, trade: result.trade }
    } catch (err) {
      return { ok: false, error: err.message }
    } finally {
      setBusy(false)
    }
  }

  const reset = async () => {
    setBusy(true)
    try {
      setData(await resetPortfolio())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const sharesOwned = (ticker) => data?.positions.find((p) => p.ticker === ticker)?.shares ?? 0

  return { data, error, busy, trade, reset, sharesOwned }
}
