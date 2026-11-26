import { useMemo, useState } from 'react'
import { price } from '../format'
import LineChart from './LineChart'

const COLORS = { base: '#3b82f6', other: '#f59e0b' }
const shortCode = (ticker) => ticker.replace(/\.BK$/, '')
const percent = (v) => (v == null ? 'N/A' : `${v > 0 ? '+' : ''}${v.toFixed(1)}%`)

/** Closes -> % change since the first day in the range (first day = 0%). */
function toPercent(candles) {
  const first = candles[0]?.close
  return candles.map((c) => ({ time: c.time, value: (c.close / first - 1) * 100 }))
}

/**
 * Two stocks as % change on one chart.
 * base / other: price responses ({ ticker, candles }); other may still be loading (null).
 */
export default function ComparePanel({ base, other, otherLoading, otherError, theme }) {
  const [hoverTime, setHoverTime] = useState(null)
  const sameStock = Boolean(other && base.ticker === other.ticker)

  const stocks = useMemo(() => {
    const list = [{ id: 'base', data: base }]
    if (other && base.ticker !== other.ticker) list.push({ id: 'other', data: other })
    return list.map(({ id, data }) => {
      const points = toPercent(data.candles)
      const closeByDate = new Map(data.candles.map((c) => [c.time, c.close]))
      const pctByDate = new Map(points.map((p) => [p.time, p.value]))
      return { id, color: COLORS[id], ticker: data.ticker, points, closeByDate, pctByDate }
    })
  }, [base, other])

  const series = useMemo(() => stocks.map(({ id, color, points }) => ({ id, color, points })), [stocks])

  const firstDate = base.candles[0]?.time
  const shownDate = hoverTime ?? base.candles.at(-1)?.time

  return (
    <>
      <p className="compare-explain">
        Both lines start at <strong>0%</strong> on the first day shown, so you can compare how much each price moved,
        even though the prices themselves are different.
      </p>
      {otherError && <p className="message error">Can't compare: {otherError}</p>}
      {sameStock && <p className="message">That's the same stock. Pick a different one to compare.</p>}

      <div className="readout">
        <span className="readout-date">
          {shownDate} vs {firstDate}
        </span>
        {stocks.map((s) => (
          <span key={s.id}>
            <span className="readout-ma" style={{ color: s.color }}>
              {shortCode(s.ticker)}
            </span>{' '}
            <span className="readout-value">{percent(s.pctByDate.get(shownDate))}</span>
            <span className="readout-zone"> ({price(s.closeByDate.get(shownDate))} THB)</span>
          </span>
        ))}
        {otherLoading && !other && <span className="readout-zone">Loading the second stock...</span>}
      </div>

      <div className={otherLoading ? 'chart-wrap loading' : 'chart-wrap'}>
        <LineChart series={series} theme={theme} onHover={setHoverTime} />
      </div>
    </>
  )
}
