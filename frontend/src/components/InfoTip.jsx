import { useId, useLayoutEffect, useRef, useState } from 'react'
import { GLOSSARY } from '../glossary'

/**
 * Explains a term from the glossary on hover, keyboard focus, or tap.
 * - No `label`: shows a small "?" button.
 * - With `label`: the label text itself is the trigger (dotted underline).
 * `extra` adds a sentence, e.g. why a value is missing.
 */
export default function InfoTip({ term, label, extra }) {
  const { title, text } = GLOSSARY[term]
  const [open, setOpen] = useState(false)
  const bubbleRef = useRef(null)
  const id = useId()

  // Center the bubble over the trigger, but keep it inside the screen (phones).
  // Uses a plain `left` value (not a CSS transform) so the bubble can't make the page wider.
  useLayoutEffect(() => {
    if (!open) return
    const bubble = bubbleRef.current
    const anchor = bubble.parentElement.getBoundingClientRect()
    const width = bubble.offsetWidth
    const margin = 8
    const centered = anchor.left + anchor.width / 2 - width / 2
    const screenWidth = document.documentElement.clientWidth // excludes the scrollbar
    const clamped = Math.min(Math.max(centered, margin), screenWidth - margin - width)
    bubble.style.left = `${clamped - anchor.left}px`
  }, [open])

  return (
    <span className="tip" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        className={label ? 'tip-label' : 'tip-icon'}
        aria-label={label ? undefined : `What is ${title}?`}
        aria-describedby={id}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen(true)} // touch screens: tap to open, tap elsewhere to close
        onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
      >
        {label ?? '?'}
      </button>
      <span ref={bubbleRef} id={id} role="tooltip" className={open ? 'tip-bubble open' : 'tip-bubble'}>
        <strong>{title}:</strong> {text}
        {extra && <> {extra}</>}
      </span>
    </span>
  )
}
