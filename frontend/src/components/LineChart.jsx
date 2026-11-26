import { useEffect, useRef } from 'react'
import { createChart, LineSeries, LineStyle } from 'lightweight-charts'
import { applyTheme, BASE_OPTIONS, LEVEL_COLOR } from '../chartTheme'

const percent = (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`

/**
 * Several lines on one shared scale (comparisons, backtest results, predictions).
 * series:   [{ id, color, points: [{ time, value }], dashed? }]
 * format:   how axis labels look (default: +1.2%)
 * baseline: value for a dashed reference line (e.g. 0% or the starting cash), or null for none
 * onHover(time | null) fires as the mouse moves; null = mouse left the chart.
 */
export default function LineChart({ series, theme, onHover, format = percent, baseline = 0 }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(new Map()) // id -> chart series
  const onHoverRef = useRef(onHover)
  const formatRef = useRef(format)
  const baselineRef = useRef(baseline)

  useEffect(() => {
    onHoverRef.current = onHover
    formatRef.current = format
  }, [onHover, format])

  useEffect(() => {
    const chart = createChart(containerRef.current, BASE_OPTIONS)
    chart.subscribeCrosshairMove((param) => onHoverRef.current?.(param.time ?? null))
    chartRef.current = chart
    const lines = seriesRef.current
    return () => {
      chart.remove()
      chartRef.current = null
      lines.clear()
    }
  }, [])

  useEffect(() => {
    applyTheme(chartRef.current, theme)
  }, [theme])

  useEffect(() => {
    const chart = chartRef.current
    const existing = seriesRef.current
    for (const s of series) {
      let line = existing.get(s.id)
      if (!line) {
        line = chart.addSeries(LineSeries, {
          lineWidth: 2,
          priceLineVisible: false,
          crosshairMarkerVisible: false,
          priceFormat: { type: 'custom', formatter: (v) => formatRef.current(v), minMove: 0.01 },
        })
        if (existing.size === 0 && baselineRef.current != null) {
          line.createPriceLine({
            price: baselineRef.current,
            color: LEVEL_COLOR,
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
          })
        }
        existing.set(s.id, line)
      }
      line.applyOptions({ color: s.color, lineStyle: s.dashed ? LineStyle.Dashed : LineStyle.Solid })
      line.setData(s.points)
    }
    for (const [id, line] of existing) {
      if (!series.some((s) => s.id === id)) {
        chart.removeSeries(line)
        existing.delete(id)
      }
    }
    chart.timeScale().fitContent()
  }, [series])

  return <div ref={containerRef} className="chart" />
}
