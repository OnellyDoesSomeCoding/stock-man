// Number formatting shared by the chart readout and stats card.

const NA = 'N/A'
const compactFmt = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })

/** 37.3 -> "37.30" */
export const price = (n) =>
  n == null ? NA : n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** 789284913152 -> "789.3B" */
export const compact = (n) => (n == null ? NA : compactFmt.format(n))

/** Adds "+" in front of positive numbers: 1.5 -> "+1.50" */
export const signed = (n, fmt = price) => (n == null ? NA : `${n > 0 ? '+' : ''}${fmt(n)}`)

/** ISO timestamp -> local "13:25" */
export const clock = (iso) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
