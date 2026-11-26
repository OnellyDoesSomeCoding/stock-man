import { useEffect, useState } from 'react'
import { addToWatchlist, fetchWatchlist, removeFromWatchlist } from './api'

/**
 * The saved watchlist (stored by the backend in SQLite).
 * items: null while the first load is running, then an array of stats objects.
 * pending: tickers with an add/remove request still on its way.
 */
export default function useWatchlist() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [pending, setPending] = useState([])

  useEffect(() => {
    const ctrl = new AbortController()
    fetchWatchlist(ctrl.signal)
      .then((data) => setItems(data.items))
      .catch((err) => {
        if (err.name === 'AbortError') return
        setError(err.message)
        setItems([])
      })
    return () => ctrl.abort()
  }, [])

  const track = async (ticker, work) => {
    setError(null)
    setPending((p) => [...p, ticker])
    try {
      await work()
    } catch (err) {
      setError(err.message)
    } finally {
      setPending((p) => p.filter((t) => t !== ticker))
    }
  }

  const add = (ticker) =>
    track(ticker, async () => {
      const item = await addToWatchlist(ticker)
      setItems((list) => [...(list ?? []).filter((i) => i.ticker !== item.ticker), item])
    })

  // Remove from the screen right away; put it back if the backend says no.
  const remove = (ticker) =>
    track(ticker, async () => {
      const before = items
      setItems((list) => list.filter((i) => i.ticker !== ticker))
      try {
        await removeFromWatchlist(ticker)
      } catch (err) {
        setItems(before)
        throw err
      }
    })

  const has = (ticker) => Boolean(items?.some((i) => i.ticker === ticker))

  return { items, error, pending, add, remove, has }
}
