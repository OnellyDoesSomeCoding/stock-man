import { useState } from 'react'
import { price } from '../format'
import InfoTip from './InfoTip'

const shortCode = (ticker) => ticker.replace(/\.BK$/, '')

/**
 * Buy / sell the current stock with fake money, at its latest price.
 * Render with key={ticker} so the form and message reset when the stock changes.
 */
export default function TradeBox({ stats, portfolio }) {
  const [sharesText, setSharesText] = useState('100')
  const [message, setMessage] = useState(null) // { text, error }

  const code = shortCode(stats.ticker)
  const cash = portfolio.data?.cash
  const owned = portfolio.sharesOwned(stats.ticker)
  const shares = /^\d+$/.test(sharesText) ? Number(sharesText) : 0
  const cost = stats.price != null ? shares * stats.price : null
  const maxAffordable = cash != null && stats.price ? Math.floor(cash / stats.price) : 0

  let blocked = null // reason both buttons are off
  if (portfolio.data === null) blocked = portfolio.error ?? 'Loading your portfolio...'
  else if (stats.stale || stats.price == null) blocked = 'Trading paused: no fresh price right now.'

  const canBuy = !blocked && shares > 0 && cost <= cash
  const canSell = !blocked && shares > 0 && shares <= owned

  // One line under the form: why trading is off, the last result, or a "not enough cash" hint.
  let note = null
  if (blocked) note = { text: blocked }
  else if (message) note = message
  else if (shares > 0 && cost > cash)
    note = { text: `Not enough cash for ${shares.toLocaleString()} shares (you can buy up to ${maxAffordable.toLocaleString()}).` }

  const submit = async (side) => {
    setMessage(null)
    const result = await portfolio.trade(stats.ticker, side, shares)
    if (!result.ok) return setMessage({ text: result.error, error: true })
    const t = result.trade
    setMessage({
      text: `${side === 'buy' ? 'Bought' : 'Sold'} ${t.shares.toLocaleString()} ${code} at ${price(t.price)} THB = ${price(t.amount)} THB.`,
    })
  }

  return (
    <div className="trade">
      <div className="trade-head">
        <span className="trade-title">
          Paper trade <InfoTip term="paperTrading" />
        </span>
        <span className="trade-holdings">
          You own <strong>{owned.toLocaleString()}</strong> <InfoTip term="shares" label="shares" /> · <InfoTip term="cash" label="Cash" />{' '}
          <strong>{cash != null ? `${price(cash)} THB` : '...'}</strong>
        </span>
      </div>

      <div className="trade-form">
        <label className="trade-input">
          <input
            type="number"
            inputMode="numeric"
            min="1"
            step="1"
            value={sharesText}
            onChange={(e) => setSharesText(e.target.value)}
            aria-label={`Number of ${code} shares`}
          />
          <span>shares</span>
        </label>
        <button
          type="button"
          className="chip"
          onClick={() => setSharesText(String(maxAffordable))}
          disabled={Boolean(blocked) || maxAffordable === 0}
          title="As many shares as your cash can buy"
        >
          Max
        </button>
        <span className="trade-cost">≈ {cost != null ? `${price(cost)} THB` : 'N/A'}</span>
        <div className="trade-buttons">
          <button type="button" className="buy" disabled={!canBuy || portfolio.busy} onClick={() => submit('buy')}>
            Buy
          </button>
          <button type="button" className="sell" disabled={!canSell || portfolio.busy} onClick={() => submit('sell')}>
            Sell
          </button>
        </div>
      </div>

      <p className={note?.error ? 'trade-message error' : 'trade-message'} aria-live="polite">
        {note?.text}
      </p>
    </div>
  )
}
