import { useMemo, useState } from 'react'
import { fetchBacktest } from '../api'
import { compact, price, signed } from '../format'
import useFetch from '../useFetch'
import InfoTip from './InfoTip'
import LineChart from './LineChart'
import { DOWN, UP } from './PriceChart'

const STRATEGIES = [
  { id: 'price_above_ma50', label: 'Price vs 50-day average' },
  { id: 'ma20_above_ma50', label: '20 vs 50-day average' },
  { id: 'rsi_30_70', label: 'RSI 30 / 70' },
]
const RANGES = ['1y', '5y']
const RULE_COLOR = '#3b82f6'
const HOLD_COLOR = '#9ca3af'
const thb = (v) => `${price(v)} THB`
const pct = (v) => `${signed(v)}%`
const color = (v) => (v == null || v === 0 ? undefined : v > 0 ? UP : DOWN)

/** Replay a trading rule over past prices and compare it with buy-and-hold. */
export default function BacktestPanel({ ticker, theme }) {
  const [strategy, setStrategy] = useState(STRATEGIES[0].id)
  const [range, setRange] = useState('5y')
  const [hoverTime, setHoverTime] = useState(null)
  const bt = useFetch(`${ticker}|${strategy}|${range}`, (signal) => fetchBacktest(ticker, strategy, range, signal))
  const data = bt.data

  const series = useMemo(
    () =>
      data
        ? [
            { id: 'rule', color: RULE_COLOR, points: data.equity },
            { id: 'hold', color: HOLD_COLOR, points: data.buy_hold_equity, dashed: true },
          ]
        : [],
    [data],
  )
  const byDate = useMemo(() => {
    if (!data) return null
    const hold = new Map(data.buy_hold_equity.map((p) => [p.time, p.value]))
    return new Map(data.equity.map((p) => [p.time, { rule: p.value, hold: hold.get(p.time) }]))
  }, [data])

  const shownDate = hoverTime ?? data?.end
  const shown = byDate?.get(shownDate)
  const r = data?.result
  const beat = data && r.return_pct > data.buy_hold.return_pct

  return (
    <div className="lab-panel">
      <div className="lab-controls">
        <div className="indicators-group" role="group" aria-label="Trading rule">
          {STRATEGIES.map((s) => (
            <button
              key={s.id}
              type="button"
              className={s.id === strategy ? 'chip active' : 'chip'}
              aria-pressed={s.id === strategy}
              onClick={() => setStrategy(s.id)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="ranges" role="group" aria-label="Test period">
          {RANGES.map((x) => (
            <button key={x} className={x === range ? 'active' : ''} onClick={() => setRange(x)}>
              Last {x.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {bt.error ? (
        <p className="message error">{bt.error}</p>
      ) : !data ? (
        <p className="message">Running the backtest...</p>
      ) : (
        <div className={bt.loading ? 'lab-results loading' : 'lab-results'}>
          <p className="lab-rule">
            <strong>Rule:</strong> {data.rule}
          </p>
          <p className="lab-verdict">
            Starting with {thb(data.starting_cash)} on {data.start}, the rule ended with{' '}
            <strong style={{ color: color(r.return_pct) }}>
              {thb(r.final_value)} ({pct(r.return_pct)})
            </strong>
            . <InfoTip term="buyAndHold" label="Buy and hold" /> ended with{' '}
            <strong style={{ color: color(data.buy_hold.return_pct) }}>
              {thb(data.buy_hold.final_value)} ({pct(data.buy_hold.return_pct)})
            </strong>
            . {beat ? 'The rule did better this time.' : 'The rule did worse than doing nothing clever.'}
          </p>

          <div className="table-wrap">
            <table className="positions lab-table">
              <thead>
                <tr>
                  <th scope="col"></th>
                  <th scope="col" className="num">
                    <span className="swatch" style={{ background: RULE_COLOR }} /> Rule
                  </th>
                  <th scope="col" className="num">
                    <span className="swatch" style={{ background: HOLD_COLOR }} /> Buy and hold
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">Final value (THB)</th>
                  <td className="num">{price(r.final_value)}</td>
                  <td className="num">{price(data.buy_hold.final_value)}</td>
                </tr>
                <tr>
                  <th scope="row">Return</th>
                  <td className="num" style={{ color: color(r.return_pct) }}>{pct(r.return_pct)}</td>
                  <td className="num" style={{ color: color(data.buy_hold.return_pct) }}>{pct(data.buy_hold.return_pct)}</td>
                </tr>
                <tr>
                  <th scope="row">
                    Biggest drop <InfoTip term="maxDrawdown" />
                  </th>
                  <td className="num">-{r.max_drawdown_pct}%</td>
                  <td className="num">-{data.buy_hold.max_drawdown_pct}%</td>
                </tr>
              </tbody>
            </table>
          </div>

          <dl className="lab-facts">
            <div>
              <dt>Trades</dt>
              <dd>{r.trades}</dd>
            </div>
            <div>
              <dt>
                Win rate <InfoTip term="winRate" />
              </dt>
              <dd>{r.win_rate_pct == null ? 'N/A' : `${r.win_rate_pct}% of ${r.round_trips}`}</dd>
            </div>
            <div>
              <dt>
                Fees paid <InfoTip term="brokerFee" />
              </dt>
              <dd>{thb(r.fees_paid)}</dd>
            </div>
            <div>
              <dt>
                Time in market <InfoTip term="timeInMarket" />
              </dt>
              <dd>{r.time_in_market_pct}%</dd>
            </div>
          </dl>

          <div className="readout">
            <span className="readout-date">{shownDate}</span>
            <span>
              <span className="readout-ma" style={{ color: RULE_COLOR }}>Rule</span>{' '}
              <span className="readout-value">{shown ? thb(shown.rule) : 'N/A'}</span>
            </span>
            <span>
              <span className="readout-ma" style={{ color: HOLD_COLOR }}>Buy and hold</span>{' '}
              <span className="readout-value">{shown ? thb(shown.hold) : 'N/A'}</span>
            </span>
          </div>
          <div className="chart-wrap">
            <LineChart
              series={series}
              theme={theme}
              onHover={setHoverTime}
              format={(v) => compact(v)}
              baseline={data.starting_cash}
            />
          </div>

          {data.trades.length > 0 && (
            <details className="trades">
              <summary>All {data.trades.length} trades</summary>
              <ul>
                {data.trades.map((t, i) => (
                  <li key={i}>
                    <span className="trade-when">{t.time}</span>
                    <span className={t.side === 'buy' ? 'side buy' : 'side sell'}>{t.side === 'buy' ? 'Buy' : 'Sell'}</span>
                    <span>
                      {t.shares.toLocaleString()} @ {price(t.price)}
                    </span>
                    <span className="num" style={{ color: color(t.profit) }}>
                      {t.profit == null ? '' : `${signed(t.profit)} THB`}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          )}

          <p className="note">
            How it's tested: the rule decides at each day's close and trades at the next day's opening price, with a{' '}
            {data.fee_rate_pct}% fee per trade. The test starts once the rule has enough history for its averages
            ({data.start}). Dividends are ignored. A rule that worked in the past can fail in the future.
          </p>
        </div>
      )}
    </div>
  )
}
