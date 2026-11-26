import { useEffect, useRef } from 'react'
import { CandlestickSeries, createChart, HistogramSeries, LineSeries, LineStyle } from 'lightweight-charts'
import { applyTheme, BASE_OPTIONS, LEVEL_COLOR } from '../chartTheme'

export const UP = '#16a34a' // closed higher than it opened
export const DOWN = '#dc2626' // closed lower than it opened

const RSI_PANE = 1 // second pane, under the price chart

/**
 * Candlestick chart with volume bars underneath, plus optional lines on top.
 * lines: [{ id, color, points: [{ time, value }], visible }]  (e.g. moving averages)
 * rsi:   { points, color, levels: [70, 30], visible }  drawn in its own pane below
 * onHover(candle | null) fires as the mouse moves; null = mouse left the chart.
 */
export default function PriceChart({ candles, lines = [], rsi = null, theme, onHover }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const lineSeriesRef = useRef(new Map()) // line id -> chart series
  const rsiSeriesRef = useRef(null)
  const onHoverRef = useRef(onHover)

  // Keep the latest callback without re-subscribing to the chart.
  useEffect(() => {
    onHoverRef.current = onHover
  }, [onHover])

  // Create the chart once.
  useEffect(() => {
    const chart = createChart(containerRef.current, BASE_OPTIONS)

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: UP,
      downColor: DOWN,
      wickUpColor: UP,
      wickDownColor: DOWN,
      borderVisible: false,
    })
    candleSeries.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.28 } })

    // Volume gets its own hidden scale, squeezed into the bottom 22% of the chart.
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      lastValueVisible: false,
      priceLineVisible: false,
    })
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } })

    chart.subscribeCrosshairMove((param) => {
      const candle = param.time ? param.seriesData.get(candleSeries) : null
      const volume = param.time ? param.seriesData.get(volumeSeries) : null
      onHoverRef.current?.(candle ? { ...candle, volume: volume?.value } : null)
    })

    chartRef.current = { chart, candleSeries, volumeSeries }
    const lineSeries = lineSeriesRef.current
    return () => {
      chart.remove()
      chartRef.current = null
      lineSeries.clear()
      rsiSeriesRef.current = null
    }
  }, [])

  // Light/dark colors.
  useEffect(() => {
    applyTheme(chartRef.current.chart, theme)
  }, [theme])

  // New data.
  useEffect(() => {
    const { chart, candleSeries, volumeSeries } = chartRef.current
    candleSeries.setData(candles.map(({ time, open, high, low, close }) => ({ time, open, high, low, close })))
    volumeSeries.setData(
      candles.map((c) => ({
        time: c.time,
        value: c.volume,
        color: (c.close >= c.open ? UP : DOWN) + '66', // 66 = ~40% opacity
      })),
    )
    chart.timeScale().fitContent()
  }, [candles])

  // Lines (moving averages). Created the first time each id appears; hidden ones stay loaded.
  useEffect(() => {
    const { chart } = chartRef.current
    const existing = lineSeriesRef.current
    for (const line of lines) {
      let series = existing.get(line.id)
      if (!series) {
        series = chart.addSeries(LineSeries, {
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        })
        existing.set(line.id, series)
      }
      series.applyOptions({ color: line.color, visible: line.visible })
      series.setData(line.points)
    }
    for (const [id, series] of existing) {
      if (!lines.some((l) => l.id === id)) {
        chart.removeSeries(series)
        existing.delete(id)
      }
    }
  }, [lines])

  // RSI pane. Removing its only series also removes the (now empty) pane.
  const rsiVisible = Boolean(rsi?.visible)
  useEffect(() => {
    const { chart } = chartRef.current
    if (!rsiVisible) {
      if (rsiSeriesRef.current) chart.removeSeries(rsiSeriesRef.current)
      rsiSeriesRef.current = null
      return
    }
    if (!rsiSeriesRef.current) {
      const series = chart.addSeries(
        LineSeries,
        {
          color: rsi.color,
          lineWidth: 2,
          priceLineVisible: false,
          crosshairMarkerVisible: false,
          priceFormat: { type: 'price', precision: 0, minMove: 1 },
          autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }), // always 0-100
        },
        RSI_PANE,
      )
      // Own spacing: otherwise this pane copies the price chart's (which leaves room for volume bars).
      series.priceScale().applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } })
      for (const level of rsi.levels) {
        series.createPriceLine({ price: level, color: LEVEL_COLOR, lineWidth: 1, lineStyle: LineStyle.Dashed })
      }
      const [pricePane, rsiPane] = chart.panes()
      pricePane.setStretchFactor(3) // price chart gets 3/4 of the height, RSI 1/4
      rsiPane.setStretchFactor(1)
      rsiSeriesRef.current = series
    }
    rsiSeriesRef.current.setData(rsi.points)
  }, [rsi, rsiVisible])

  return <div ref={containerRef} className={rsiVisible ? 'chart with-rsi' : 'chart'} />
}
