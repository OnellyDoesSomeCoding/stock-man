import { price, signed } from '../format'
import InfoTip from './InfoTip'
import { DOWN, UP } from './PriceChart'

const shortCode = (ticker) => ticker.replace(/\.BK$/, '')
const plColor = (v) => (v == null || v === 0 ? undefined : v > 0 ? UP : DOWN)
const when = (iso) =>
  new Date(iso).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

function Summary({ label, term, value, sub, color }) {
  return (
    <div className="tile">
      <dt>
        {label} <InfoTip term={term} />
      </dt>
      <dd style={{ color }}>{value}</dd>
      {sub && <dd className="tile-sub">{sub}</dd>}
    </div>
  )
}

/** Paper portfolio: totals, what you own, and recent trades. */
export default function PortfolioCard({ portfolio, onSelect }) {
  const { data, error, busy } = portfolio

  const confirmReset = () => {
    if (window.confirm('Start over with 100,000 THB? This deletes all your paper trades.')) portfolio.reset()
  }

  return (
    <section className="card portfolio" aria-labelledby="portfolio-title">
      <div className="card-top">
        <h2 id="portfolio-title">
          My paper portfolio <InfoTip term="paperTrading" />
        </h2>
        {data?.trade_count > 0 && (
          <button type="button" className="chip" onClick={confirmReset} disabled={busy}>
            Reset
          </button>
        )}
      </div>

      {error && <p className="message error">{error}</p>}
      {!data ? (
        !error && <p className="message">Loading...</p>
      ) : (
        <>
          <dl className="stats-grid portfolio-summary">
            <Summary
              label="Total value"
              term="totalValue"
              value={`${price(data.total_value)} THB`}
              sub={`Started with ${price(data.starting_cash)}`}
            />
            <Summary
              label="Profit / loss"
              term="profitLoss"
              value={`${signed(data.total_pl)} THB`}
              sub={`${signed(data.total_pl_pct)}% since start`}
              color={plColor(data.total_pl)}
            />
            <Summary label="Cash" term="cash" value={`${price(data.cash)} THB`} sub={`In stocks: ${price(data.holdings_value)}`} />
          </dl>

          {data.positions.length === 0 ? (
            <p className="message">
              You don't own any stocks yet. Open one and use <strong>Paper trade</strong> on its card to buy.
            </p>
          ) : (
            <div className="table-wrap">
              <table className="positions">
                <thead>
                  <tr>
                    <th scope="col">Stock</th>
                    <th scope="col" className="num">Shares</th>
                    <th scope="col" className="num">
                      Avg cost <InfoTip term="avgCost" />
                    </th>
                    <th scope="col" className="num">Price</th>
                    <th scope="col" className="num">
                      Value <InfoTip term="marketValue" />
                    </th>
                    <th scope="col" className="num">
                      Profit / loss <InfoTip term="profitLoss" />
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.positions.map((p) => (
                    <tr key={p.ticker}>
                      <th scope="row">
                        <button type="button" className="link" onClick={() => onSelect(p.ticker)}>
                          {shortCode(p.ticker)}
                        </button>
                      </th>
                      <td className="num">{p.shares.toLocaleString()}</td>
                      <td className="num">{price(p.avg_cost)}</td>
                      <td className="num">{price(p.price)}</td>
                      <td className="num">{price(p.market_value)}</td>
                      <td className="num" style={{ color: plColor(p.unrealized_pl) }}>
                        {signed(p.unrealized_pl)}
                        <span className="pl-pct"> ({signed(p.unrealized_pl_pct)}%)</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data.trades.length > 0 && (
            <details className="trades">
              <summary>
                Recent trades ({data.trade_count}){' '}
                {data.realized_pl !== 0 && (
                  <span style={{ color: plColor(data.realized_pl) }}>
                    · realized {signed(data.realized_pl)} THB
                  </span>
                )}
              </summary>
              <ul>
                {data.trades.map((t) => (
                  <li key={t.id}>
                    <span className="trade-when">{when(t.executed_at)}</span>
                    <span className={t.side === 'buy' ? 'side buy' : 'side sell'}>{t.side === 'buy' ? 'Buy' : 'Sell'}</span>
                    <span>
                      {t.shares.toLocaleString()} {shortCode(t.ticker)} @ {price(t.price)}
                    </span>
                    <span className="num">{price(t.amount)} THB</span>
                  </li>
                ))}
              </ul>
            </details>
          )}

          <p className="note">
            Fake money for practice. Trades use the latest free price (can be delayed), with no broker fees and no
            market-hours check.
          </p>
        </>
      )}
    </section>
  )
}
