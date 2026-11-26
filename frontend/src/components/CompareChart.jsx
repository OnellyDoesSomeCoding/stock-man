import { useEffect, useRef } from 'react'
import { createChart, LineSeries, LineStyle } from 'lightweight-charts'
import { applyTheme, BASE_OPTIONS, LEVEL_COLOR } from '../chartTheme'

const percent = (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`

/**
 * Line chart of % change for several stocks on one shared scale.
 * series: [{ id, color, points: [{ time, value }] }]   (value = % change, 0 = first day)
 * onHover(time | null) fires as the mouse moves; null = mouse left the chart.
 */
export default function CompareChart({ series, theme, onHover }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(new Map()) // id -> chart series
  const onHoverRef = useRef(onHover)

  useEffect(() => {
    onHoverRef.current = onHover
  }, [onHover])

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
          priceFormat: { type: 'custom', formatter: percent, minMove: 0.1 },
        })
        if (existing.size === 0) {
          // Dashed line at 0% = "same price as on the first day".
          line.createPriceLine({ price: 0, color: LEVEL_COLOR, lineWidth: 1, lineStyle: LineStyle.Dashed })
        }
        existing.set(s.id, line)
      }
      line.applyOptions({ color: s.color })
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
