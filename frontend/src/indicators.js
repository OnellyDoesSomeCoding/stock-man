// Moving-average lines the chart can show. ~21 trading days = 1 month, ~245 = 1 year.
export const MA_LINES = [
  { period: 20, color: '#3b82f6', about: '≈ 1 month' },
  { period: 50, color: '#f59e0b', about: '≈ 2½ months' },
  { period: 200, color: '#a855f7', about: '≈ 10 months' },
]

export const MA_DEFAULT_ON = [20, 50]

// RSI: 0-100. Above HIGH = maybe overbought, below LOW = maybe oversold.
export const RSI = { period: 14, color: '#0891b2', high: 70, low: 30 }

export function rsiZone(value) {
  if (value == null) return null
  if (value >= RSI.high) return 'maybe overbought'
  if (value <= RSI.low) return 'maybe oversold'
  return `between ${RSI.low} and ${RSI.high}`
}
