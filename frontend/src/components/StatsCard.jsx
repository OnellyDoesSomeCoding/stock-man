import { GLOSSARY } from '../glossary'
import { clock, compact, price, signed } from '../format'
import InfoTip from './InfoTip'
import { DOWN, UP } from './PriceChart'

function Tile({ term, value, extra }) {
  return (
    <div className="tile">
      <dt>
        {GLOSSARY[term].title} <InfoTip term={term} extra={extra} />
      </dt>
      <dd>{value}</dd>
    </div>
  )
}

function WatchButton({ watched, busy, onClick }) {
  return (
    <button
      type="button"
      className={watched ? 'watch-toggle on' : 'watch-toggle'}
      aria-pressed={watched}
      disabled={busy}
      onClick={onClick}
      title={watched ? 'Remove from your watchlist' : 'Add to your watchlist'}
    >
      <span aria-hidden="true">{watched ? '★' : '☆'}</span> {watched ? 'Watching' : 'Watch'}
    </button>
  )
}

/** Headline numbers for one stock: price, today's change, market cap, P/E. */
export default function StatsCard({ stats, loading, watched, watchBusy, onToggleWatch }) {
  const color = stats.change == null ? undefined : stats.change >= 0 ? UP : DOWN
  const currency = stats.currency ?? 'THB'

  return (
    <section className={loading ? 'card stats loading' : 'card stats'}>
      <div className="stats-head">
        <div>
          <h2 className="stats-name">{stats.name ?? stats.ticker}</h2>
          <span className="stats-ticker">
            {stats.ticker} <InfoTip term="ticker" />
          </span>
        </div>
        <div className="stats-side">
          <WatchButton watched={watched} busy={watchBusy || loading} onClick={onToggleWatch} />
          <span className="stats-updated">
            {stats.stale ? 'Saved copy from ' : 'Updated '}
            {clock(stats.updated_at)}
          </span>
        </div>
      </div>

      <div className="stats-price-row">
        <span className="stats-price">
          {price(stats.price)} <span className="stats-currency">{currency}</span> <InfoTip term="price" />
        </span>
        <span className="stats-change">
          <span style={{ color }}>
            {signed(stats.change)} ({signed(stats.change_pct)}%)
          </span>{' '}
          <InfoTip term="change" />
        </span>
      </div>

      <dl className="stats-grid">
        <Tile term="marketCap" value={stats.market_cap == null ? 'N/A' : `${compact(stats.market_cap)} ${currency}`} />
        <Tile term="pe" value={price(stats.pe_ratio)} extra={stats.pe_ratio == null ? GLOSSARY.pe.missing : null} />
        <Tile term="previousClose" value={`${price(stats.previous_close)} ${currency}`} />
      </dl>
    </section>
  )
}
