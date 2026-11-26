import { useEffect, useMemo, useState } from 'react'
import { fetchPrices, fetchStats } from './api'
import ComparePanel from './components/ComparePanel'
import InfoTip from './components/InfoTip'
import PriceChart, { DOWN, UP } from './components/PriceChart'
import StatsCard from './components/StatsCard'
import TickerSearch from './components/TickerSearch'
import Watchlist from './components/Watchlist'
import { compact, price } from './format'
import { MA_DEFAULT_ON, MA_LINES, RSI, rsiZone } from './indicators'
import useFetch from './useFetch'
import useWatchlist from './useWatchlist'

const RANGES = ['1m', '3m', '6m', '1y', '5y']
const MA_PERIODS = MA_LINES.map((l) => l.period)
// Always fetch every indicator; the toggles only show/hide (no re-download when clicking).
const INDICATORS = { sma: MA_PERIODS, rsi: RSI.period }

function useColorScheme() {
  const query = '(prefers-color-scheme: dark)'
  const [dark, setDark] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = (e) => setDark(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return dark ? 'dark' : 'light'
}

function Chip({ active, color, title, onClick, children }) {
  return (
    <button
      type="button"
      className={active ? 'chip active' : 'chip'}
      aria-pressed={active}
      title={title}
      onClick={onClick}
    >
      <span className="chip-swatch" style={{ background: color }} />
      {children}
    </button>
  )
}

/** On/off buttons for the indicators drawn on the chart. */
function IndicatorToggles({ maOn, onToggleMa, rsiOn, onToggleRsi }) {
  return (
    <div className="indicators">
      <div className="indicators-group">
        <span className="indicators-label">
          Moving average <InfoTip term="movingAverage" />
        </span>
        {MA_LINES.map(({ period, color, about }) => (
          <Chip
            key={period}
            active={maOn.includes(period)}
            color={color}
            title={`Average of the last ${period} trading days (${about})`}
            onClick={() => onToggleMa(period)}
          >
            {period} days
          </Chip>
        ))}
      </div>
      <div className="indicators-group">
        <span className="indicators-label">
          RSI <InfoTip term="rsi" />
        </span>
        <Chip active={rsiOn} color={RSI.color} title={`RSI over the last ${RSI.period} trading days`} onClick={onToggleRsi}>
          {RSI.period} days
        </Chip>
      </div>
    </div>
  )
}

/** The day under the mouse (or the latest day): open / high / low / close / volume + visible indicators. */
function CandleReadout({ candle, averages, rsi }) {
  if (!candle) return null
  const up = candle.close >= candle.open
  const fields = [
    ['open', price(candle.open)],
    ['high', price(candle.high)],
    ['low', price(candle.low)],
    ['close', price(candle.close)],
    ['volume', compact(candle.volume)],
  ]
  return (
    <div className="readout">
      <span className="readout-date">{candle.time}</span>
      {fields.map(([term, value]) => (
        <span key={term}>
          <InfoTip term={term} label={term[0].toUpperCase() + term.slice(1)} />{' '}
          <span className="readout-value" style={term === 'close' ? { color: up ? UP : DOWN } : undefined}>
            {value}
          </span>
        </span>
      ))}
      {averages.map(({ period, color, value }) => (
        <span key={period}>
          <span className="readout-ma" style={{ color }}>
            MA {period}
          </span>{' '}
          <span className="readout-value">{price(value)}</span>
        </span>
      ))}
      {rsi && (
        <span>
          <InfoTip term="rsi" label="RSI" /> <span className="readout-value">{rsi.value?.toFixed(1) ?? 'N/A'}</span>
          {rsi.zone && <span className="readout-zone"> ({rsi.zone})</span>}
        </span>
      )}
    </div>
  )
}

export default function App() {
  const [ticker, setTicker] = useState('PTT')
  const [range, setRange] = useState('1y')
  const [hovered, setHovered] = useState(null)
  const [maOn, setMaOn] = useState(MA_DEFAULT_ON)
  const [rsiOn, setRsiOn] = useState(true)
  const [compareTicker, setCompareTicker] = useState(null) // second stock, or null = normal chart
  const theme = useColorScheme()
  const watchlist = useWatchlist()

  const prices = useFetch(`${ticker}|${range}`, (signal) => fetchPrices(ticker, range, INDICATORS, signal))
  const stats = useFetch(ticker, (signal) => fetchStats(ticker, signal))
  const compare = useFetch(compareTicker && `${compareTicker}|${range}`, (signal) =>
    fetchPrices(compareTicker, range, {}, signal),
  )

  const toggleMa = (period) =>
    setMaOn((on) => (on.includes(period) ? on.filter((p) => p !== period) : [...on, period]))

  const sma = prices.data?.sma
  const lines = useMemo(
    () =>
      MA_LINES.map(({ period, color }) => ({
        id: `ma${period}`,
        color,
        points: sma?.[period] ?? [],
        visible: maOn.includes(period),
      })),
    [sma, maOn],
  )
  // period -> Map(date -> average), so the readout can look up any hovered day
  const maByDate = useMemo(
    () => new Map(MA_PERIODS.map((p) => [p, new Map((sma?.[p] ?? []).map((pt) => [pt.time, pt.value]))])),
    [sma],
  )

  const rsiPoints = prices.data?.rsi
  const rsi = useMemo(
    () => ({ points: rsiPoints ?? [], color: RSI.color, levels: [RSI.high, RSI.low], visible: rsiOn }),
    [rsiPoints, rsiOn],
  )
  const rsiByDate = useMemo(() => new Map((rsiPoints ?? []).map((pt) => [pt.time, pt.value])), [rsiPoints])

  const candles = prices.data?.candles ?? []
  const shown = hovered ?? candles.at(-1)
  const shownAverages = shown
    ? MA_LINES.filter((l) => maOn.includes(l.period)).map((l) => ({
        ...l,
        value: maByDate.get(l.period).get(shown.time),
      }))
    : []
  const shownRsiValue = shown && rsiOn ? rsiByDate.get(shown.time) : undefined
  const shownRsi = shown && rsiOn ? { value: shownRsiValue, zone: rsiZone(shownRsiValue) } : null
  const bothFailed = prices.error && stats.error // e.g. unknown ticker: show one message, not two

  // The stats card knows the full ticker ("PTT.BK") even if the user typed "ptt".
  const currentTicker = stats.data?.ticker
  const watched = Boolean(currentTicker && watchlist.has(currentTicker))
  const toggleWatch = () => (watched ? watchlist.remove(currentTicker) : watchlist.add(currentTicker))

  return (
    <main className="page">
      <header className="header">
        <h1>Stockman</h1>
        <TickerSearch current={ticker} onSelect={setTicker} />
      </header>

      <div className="layout">
        <div className="main-col">
          {bothFailed ? (
            <section className="card">
              <p className="message error">{prices.error}</p>
            </section>
          ) : (
            <>
              {stats.data ? (
                <StatsCard
                  stats={stats.data}
                  loading={stats.loading}
                  watched={watched}
                  watchBusy={watchlist.pending.includes(currentTicker) || watchlist.items === null}
                  onToggleWatch={toggleWatch}
                />
              ) : (
                <section className="card stats">
                  <p className={stats.error ? 'message error' : 'message'}>
                    {stats.error ? `Stats unavailable: ${stats.error}` : 'Loading stats...'}
                  </p>
                </section>
              )}

              <section className="card">
                <div className="card-top">
                  <h2>
                    {compareTicker ? (
                      <>
                        Compare <InfoTip term="percentChange" />
                      </>
                    ) : (
                      <>
                        Price history <InfoTip term="candle" />
                      </>
                    )}
                  </h2>
                  <div className="ranges" role="group" aria-label="Time range">
                    {RANGES.map((r) => (
                      <button key={r} className={r === range ? 'active' : ''} onClick={() => setRange(r)}>
                        {r.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="compare-bar">
                  {compareTicker ? (
                    <>
                      <span>
                        Comparing with <strong>{(compare.data?.ticker ?? compareTicker).replace(/\.BK$/, '').toUpperCase()}</strong>
                      </span>
                      <button type="button" className="chip" onClick={() => setCompareTicker(null)}>
                        × Stop comparing
                      </button>
                    </>
                  ) : (
                    <TickerSearch
                      current=""
                      onSelect={setCompareTicker}
                      placeholder="Compare with... e.g. AOT, bank"
                      label="Pick a second stock to compare with"
                      submitLabel="Compare"
                    />
                  )}
                </div>

                {prices.error ? (
                  <p className="message error">{prices.error}</p>
                ) : prices.data && compareTicker ? (
                  <ComparePanel
                    base={prices.data}
                    other={compare.data}
                    otherLoading={compare.loading}
                    otherError={compare.error}
                    theme={theme}
                  />
                ) : prices.data ? (
                  <>
                    <IndicatorToggles
                      maOn={maOn}
                      onToggleMa={toggleMa}
                      rsiOn={rsiOn}
                      onToggleRsi={() => setRsiOn((on) => !on)}
                    />
                    <CandleReadout candle={shown} averages={shownAverages} rsi={shownRsi} />
                    <div className={prices.loading ? 'chart-wrap loading' : 'chart-wrap'}>
                      <PriceChart candles={candles} lines={lines} rsi={rsi} theme={theme} onHover={setHovered} />
                    </div>
                    {prices.data.stale && (
                      <p className="message">Showing saved data: the live source is unavailable right now.</p>
                    )}
                  </>
                ) : (
                  <p className="message">Loading chart...</p>
                )}
              </section>
            </>
          )}
        </div>

        <aside className="side-col">
          <Watchlist
            items={watchlist.items}
            error={watchlist.error}
            pending={watchlist.pending}
            current={currentTicker}
            onSelect={setTicker}
            onRemove={watchlist.remove}
          />
        </aside>
      </div>

      <section className="help">
        <h3>How to read this chart</h3>
        <ul>
          <li>Each <strong>candle</strong> is one trading day.</li>
          <li>
            <span style={{ color: UP }}>Green</span> = the price ended the day <em>higher</em> than it started.{' '}
            <span style={{ color: DOWN }}>Red</span> = it ended <em>lower</em>.
          </li>
          <li>The thick <strong>body</strong> spans open to close; the thin <strong>wick</strong> spans the day's low to high.</li>
          <li>The bars at the bottom are <strong>volume</strong>: how many shares changed hands. Tall bar = busy day.</li>
          <li>
            The colored lines are <strong>moving averages</strong>: the average price of the last 20, 50 or 200 days.
            Candles above a line = the price has been rising compared with that period; below = falling.
          </li>
          <li>
            The small panel at the bottom is the <strong>RSI</strong> (0-100). Above the upper dashed line (70) the
            price rose fast lately; below the lower one (30) it fell fast.
          </li>
          <li>
            <strong>Compare with...</strong> draws two stocks as % change since the first day shown, so their moves
            can be compared fairly even when one costs much more per share.
          </li>
          <li>
            Tap or hover any <span className="tip-icon demo">?</span> or <span className="tip-label demo">dotted word</span>{' '}
            for a plain-language explanation.
          </li>
        </ul>
        <p className="note">Prices are in Thai baht (THB) and may be delayed. Past prices don't predict future ones.</p>
      </section>
    </main>
  )
}
