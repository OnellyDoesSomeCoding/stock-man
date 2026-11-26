import { useEffect, useRef, useState } from 'react'

/**
 * Runs `load(signal)` whenever `key` changes. A `null` key means "nothing to load".
 * While a new key loads, the previous data stays available (so the UI can dim it instead of going blank).
 */
export default function useFetch(key, load) {
  const [result, setResult] = useState({ key: null, data: null, error: null })
  const loadRef = useRef(load)

  useEffect(() => {
    loadRef.current = load
  })

  useEffect(() => {
    if (key === null) return
    const ctrl = new AbortController()
    loadRef.current(ctrl.signal)
      .then((data) => setResult({ key, data, error: null }))
      .catch((err) => {
        if (err.name !== 'AbortError') setResult({ key, data: null, error: err.message })
      })
    return () => ctrl.abort() // ignore the old request if the user switches quickly
  }, [key])

  if (key === null) return { data: null, error: null, loading: false }
  const loading = result.key !== key
  return { data: result.data, error: loading ? null : result.error, loading }
}
