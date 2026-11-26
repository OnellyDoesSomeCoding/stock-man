import { useEffect, useId, useRef, useState } from 'react'
import { searchTickers } from '../api'

const MIN_CHARS = 2
const DEBOUNCE_MS = 250 // wait until the user pauses typing before asking the backend

const shortCode = (ticker) => ticker.replace(/\.BK$/, '')

/**
 * Search box with suggestions: type a company name or code, pick from the list.
 * Keyboard: arrow up/down to move, Enter to pick, Escape to close.
 * Enter with nothing highlighted opens exactly what was typed (e.g. a code you already know).
 */
export default function TickerSearch({
  current,
  onSelect,
  placeholder = 'Company or code, e.g. airports, PTT',
  label = 'Search Thai stocks by company name or ticker',
  submitLabel = 'Show',
}) {
  const [text, setText] = useState(shortCode(current))
  // When the stock changes from elsewhere (e.g. a watchlist click), show its code in the box.
  const [shownFor, setShownFor] = useState(current)
  if (current !== shownFor) {
    setShownFor(current)
    setText(shortCode(current).toUpperCase())
  }
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [result, setResult] = useState({ query: null, items: [], error: null })
  const listId = useId()
  const inputRef = useRef(null)
  const selectAfterRender = useRef(false)
  const lastPointer = useRef({ x: -1, y: -1 })

  // After picking a stock the cursor stays in the box: select the text so the next search replaces it.
  useEffect(() => {
    if (!selectAfterRender.current) return
    selectAfterRender.current = false
    if (document.activeElement === inputRef.current) inputRef.current.select()
  })

  const query = text.trim()
  const searching = open && query.length >= MIN_CHARS

  useEffect(() => {
    if (!searching) return
    const ctrl = new AbortController()
    const timer = setTimeout(() => {
      searchTickers(query, ctrl.signal)
        .then((data) => setResult({ query, items: data.results, error: null }))
        .catch((err) => {
          if (err.name !== 'AbortError') setResult({ query, items: [], error: err.message })
        })
    }, DEBOUNCE_MS)
    return () => {
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [query, searching])

  const loading = searching && result.query !== query
  const items = searching ? result.items : [] // while loading, keep the previous list (dimmed)
  const activeIndex = active < items.length ? active : -1

  // Arrow keys past the visible part of the list: scroll the highlighted row into view.
  useEffect(() => {
    if (activeIndex >= 0) document.getElementById(`${listId}-${activeIndex}`)?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex, listId])

  const choose = (ticker) => {
    setText(shortCode(ticker).toUpperCase())
    setOpen(false)
    setActive(-1)
    selectAfterRender.current = true
    onSelect(ticker)
  }

  const onSubmit = (e) => {
    e.preventDefault()
    if (activeIndex >= 0) choose(items[activeIndex].ticker)
    else if (query) choose(query)
  }

  // Highlight the row under the mouse, but only when the mouse really moved:
  // when arrow keys scroll the list, rows slide under a resting pointer and would steal the highlight.
  const onRowMouseMove = (e, i) => {
    const { x, y } = lastPointer.current
    if (e.clientX === x && e.clientY === y) return
    lastPointer.current = { x: e.clientX, y: e.clientY }
    if (i !== activeIndex) setActive(i)
  }

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      if (items.length) setActive((activeIndex + 1) % items.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (items.length) setActive(activeIndex <= 0 ? items.length - 1 : activeIndex - 1)
    } else if (e.key === 'Escape') {
      setOpen(false)
      setActive(-1)
    }
  }

  let status = null
  if (searching && result.error && !loading) status = { text: result.error, error: true }
  else if (searching && loading && items.length === 0) status = { text: 'Searching...' }
  else if (searching && !loading && items.length === 0)
    status = { text: `No Thai stocks match "${query}". Try the company's English name or its code.` }

  return (
    <form className="search" onSubmit={onSubmit} role="search" aria-label={label}>
      <div className="search-box">
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            setOpen(true)
            setActive(-1)
          }}
          onKeyDown={onKeyDown}
          onFocus={(e) => e.target.select()} // typing replaces the current code
          onBlur={() => setOpen(false)}
          placeholder={placeholder}
          aria-label={label}
          role="combobox"
          aria-expanded={searching}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
          autoComplete="off"
          spellCheck={false}
        />
        {searching && (
          <div className={loading ? 'suggestions loading' : 'suggestions'}>
            {status && (
              <p className={status.error ? 'suggestions-status error' : 'suggestions-status'} aria-live="polite">
                {status.text}
              </p>
            )}
            <ul id={listId} role="listbox" aria-label="Matching stocks">
              {items.map((item, i) => (
                <li
                  key={item.ticker}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={i === activeIndex}
                  className={i === activeIndex ? 'active' : ''}
                  onMouseDown={(e) => e.preventDefault()} // keep focus in the input
                  onMouseMove={(e) => onRowMouseMove(e, i)}
                  onClick={() => choose(item.ticker)}
                >
                  <span className="suggestion-code">{shortCode(item.ticker)}</span>
                  <span className="suggestion-name">{item.name ?? ''}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <button type="submit">{submitLabel}</button>
    </form>
  )
}
