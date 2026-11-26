// Colors and options shared by every Lightweight Charts chart on the page.
import { ColorType } from 'lightweight-charts'

const THEMES = {
  light: { bg: '#ffffff', text: '#4b5563', grid: '#eef0f3', border: '#e5e7eb' },
  dark: { bg: '#16181d', text: '#9ca3af', grid: '#22252c', border: '#2d3139' },
}

export const LEVEL_COLOR = '#9ca3af' // dashed reference lines, readable in light and dark

export const BASE_OPTIONS = {
  autoSize: true, // follow the container's size
  // Keep the same dates in view when the window is resized (instead of leaving a gap).
  timeScale: { timeVisible: false, lockVisibleTimeRangeOnResize: true },
  crosshair: { mode: 0 }, // free-moving crosshair
}

export function applyTheme(chart, theme) {
  const c = THEMES[theme]
  chart.applyOptions({
    layout: { background: { type: ColorType.Solid, color: c.bg }, textColor: c.text },
    grid: { vertLines: { color: c.grid }, horzLines: { color: c.grid } },
    rightPriceScale: { borderColor: c.border },
    timeScale: { borderColor: c.border },
  })
}
