import { price, signed } from '../format'
import InfoTip from './InfoTip'
import { DOWN, UP } from './PriceChart'

const shortCode = (ticker) => ticker.replace(/\.BK$/, '')

/** Saved stocks with today's price and change. Click a row to open it. */
export default function Watchlist({ items, error, pending, current, onSelect, onRemove }) {
  return (
    <section className="card watchlist" aria-labelledby="watchlist-title">
      <h2 id="watchlist-title">
        Watchlist <InfoTip term="watchlist" />
      </h2>

      {error && <p className="message error">{error}</p>}

      {items === null ? (
        <p className="message">Loading...</p>
      ) : items.length === 0 ? (
        <p className="message">Empty for now. Open a stock and press ☆ Watch to add it here.</p>
      ) : (
        <ul className="watch-list">
          {items.map((item) => {
            const code = shortCode(item.ticker)
            const color = item.change == null ? undefined : item.change >= 0 ? UP : DOWN
            const busy = pending.includes(item.ticker)
            return (
              <li key={item.ticker} className={item.ticker === current ? 'active' : ''}>
                <button
                  type="button"
                  className="watch-row"
                  onClick={() => onSelect(item.ticker)}
                  aria-current={item.ticker === current ? 'true' : undefined}
                >
                  <span className="watch-left">
                    <span className="watch-code">{code}</span>
                    <span className="watch-name">{item.error ?? item.name ?? ''}</span>
                  </span>
                  {!item.error && (
                    <span className="watch-right">
                      <span className="watch-price">{price(item.price)}</span>
                      <span className="watch-change" style={{ color }}>
                        {signed(item.change_pct)}%
                      </span>
                    </span>
                  )}
                </button>
                <button
                  type="button"
                  className="watch-remove"
                  aria-label={`Remove ${code} from watchlist`}
                  title="Remove from watchlist"
                  disabled={busy}
                  onClick={() => onRemove(item.ticker)}
                >
                  ×
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {items?.length > 0 && <p className="note">Change = since the previous close. Prices can be up to 30 min old.</p>}
    </section>
  )
}
