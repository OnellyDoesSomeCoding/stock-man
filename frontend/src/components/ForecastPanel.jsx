import { useMemo, useState } from 'react'
import { fetchForecast } from '../api'
import { price, signed } from '../format'
import useFetch from '../useFetch'
import InfoTip from './InfoTip'
import LineChart from './LineChart'
import { DOWN, UP } from './PriceChart'

const HORIZONS = [
  { days: 1, label: 'Next day' },
  { days: 5, label: '1 week' },
  { days: 20, label: '1 month' },
]
const RANGES = ['1y', '5y']
const ACTUAL_COLOR = '#3b82f6'
const MODEL_COLOR = '#f59e0b'
const pct = (v) => (v == null ? 'N/A' : `${signed(v)}%`)

/** Simple prediction models, scored on past days against "the price won't change". */
export default function ForecastPanel({ ticker, theme }) {
  const [horizon, setHorizon] = useState(5)
  const [range, setRange] = useState('1y')
  const [selected, setSelected] = useState('regression')
  const [hoverTime, setHoverTime] = useState(null)
  const fc = useFetch(`${ticker}|${horizon}|${range}`, (signal) => fetchForecast(ticker, horizon, range, signal))
  const data = fc.data

  const model = data?.models.find((m) => m.id === selected)
  const series = useMemo(
    () =>
      data && model
        ? [
            { id: 'actual', color: ACTUAL_COLOR, points: data.actual },
            { id: 'model', color: MODEL_COLOR, points: model.points },
          ]
        : [],
    [data, model],
  )
  const byDate = useMemo(() => {
    if (!data || !model) return null
    const guess = new Map(model.points.map((p) => [p.time, p.value]))
    return new Map(data.actual.map((p) => [p.time, { actual: p.value, guess: guess.get(p.time) }]))
  }, [data, model])

  const horizonLabel = HORIZONS.find((h) => h.days === horizon).label.toLowerCase()
  const best = data ? data.models.reduce((a, b) => (b.mae < a.mae ? b : a)) : null
  const shownDate = hoverTime ?? data?.end
  const shown = byDate?.get(shownDate)

  return (
    <div className="lab-panel">
      <div className="lab-controls">
        <div className="indicators-group" role="group" aria-label="How far ahead to predict">
          <span className="indicators-label">Predict</span>
          {HORIZONS.map((h) => (
            <button
              key={h.days}
              type="button"
              className={h.days === horizon ? 'chip active' : 'chip'}
              aria-pressed={h.days === horizon}
              onClick={() => setHorizon(h.days)}
            >
              {h.label} ahead
            </button>
          ))}
        </div>
        <div className="ranges" role="group" aria-label="Test period">
          {RANGES.map((x) => (
            <button key={x} className={x === range ? 'active' : ''} onClick={() => setRange(x)}>
              Test on last {x.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {fc.error ? (
        <p className="message error">{fc.error}</p>
      ) : !data ? (
        <p className="message">Running the experiment...</p>
      ) : (
        <div className={fc.loading ? 'lab-results loading' : 'lab-results'}>
          <p className="lab-verdict">
            {best.id === 'naive' ? (
              <>
                <strong>No model beat "Tomorrow = today"</strong> over {data.samples} past guesses. That's normal:
                day-to-day price moves are mostly random, so simple patterns don't help.
              </>
            ) : (
              <>
                <strong>{best.name}</strong> missed by {Math.abs(best.vs_naive_pct)}% less than "Tomorrow = today"
                over {data.samples} past guesses. Small wins like this often disappear in a different period, so
                treat it as luck until proven otherwise.
              </>
            )}
          </p>

          <div className="table-wrap">
            <table className="positions lab-table models">
              <thead>
                <tr>
                  <th scope="col">Model (click to chart)</th>
                  <th scope="col" className="num">
                    Average miss <InfoTip term="avgMiss" />
                  </th>
                  <th scope="col" className="num">
                    vs lazy guess <InfoTip term="vsNaive" />
                  </th>
                  <th scope="col" className="num">
                    Direction right <InfoTip term="direction" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.models.map((m) => (
                  <tr
                    key={m.id}
                    className={m.id === selected ? 'selected' : ''}
                    onClick={() => setSelected(m.id)} // whole row is clickable; the name button is for keyboards
                  >
                    <th scope="row">
                      <button type="button" className="link" onClick={() => setSelected(m.id)}>
                        {m.name}
                      </button>
                      <span className="model-about">{m.about}</span>
                    </th>
                    <td className="num">
                      {price(m.mae)} THB <span className="pl-pct">({m.mape_pct}%)</span>
                    </td>
                    <td className="num" style={{ color: m.vs_naive_pct > 0 ? DOWN : m.vs_naive_pct < 0 ? UP : undefined }}>
                      {m.id === 'naive' ? 'baseline' : pct(m.vs_naive_pct)}
                    </td>
                    <td className="num">{m.direction_pct == null ? '—' : `${m.direction_pct}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.common_direction_pct != null && (
            <p className="note">
              Yardstick for "direction right": always guessing <strong>{data.common_direction}</strong> was right{' '}
              {data.common_direction_pct}% of the time in this period.
            </p>
          )}

          <div className="readout">
            <span className="readout-date">{shownDate}</span>
            <span>
              <span className="readout-ma" style={{ color: ACTUAL_COLOR }}>Real price</span>{' '}
              <span className="readout-value">{shown ? price(shown.actual) : 'N/A'}</span>
            </span>
            <span>
              <span className="readout-ma" style={{ color: MODEL_COLOR }}>{model?.name} guessed</span>{' '}
              <span className="readout-value">{shown ? price(shown.guess) : 'N/A'}</span>
              <span className="readout-zone"> ({horizonLabel} earlier)</span>
            </span>
          </div>
          <div className="chart-wrap">
            <LineChart series={series} theme={theme} onHover={setHoverTime} format={(v) => price(v)} baseline={null} />
          </div>

          <div className="outlook">
            <span className="outlook-label">
              Typical range {horizonLabel} from now <InfoTip term="outlook" />
            </span>
            <span className="outlook-range">
              {price(data.outlook.low)} – {price(data.outlook.high)} THB
            </span>
            <span className="outlook-sub">
              From {price(data.outlook.from_price)} THB ({data.outlook.from_date}): in the past, 8 times out of 10 the
              price {horizonLabel} later was between {pct(data.outlook.low_pct)} and {pct(data.outlook.high_pct)}.
              This is how much it usually moves, not a guess of where it will go.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
