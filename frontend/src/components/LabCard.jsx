import { useState } from 'react'
import BacktestPanel from './BacktestPanel'
import ForecastPanel from './ForecastPanel'
import InfoTip from './InfoTip'

const TABS = [
  { id: 'backtest', label: 'Backtest', term: 'backtest' },
  { id: 'forecast', label: 'Prediction experiment', term: 'prediction' },
]

/** Strategy lab: test trading rules and prediction models on the current stock's past prices. */
export default function LabCard({ ticker, theme }) {
  const [tab, setTab] = useState('backtest')
  const active = TABS.find((t) => t.id === tab)

  return (
    <section className="card lab" aria-labelledby="lab-title">
      <div className="card-top">
        <h2 id="lab-title">
          Strategy lab <span className="lab-ticker">{ticker.replace(/\.BK$/, '')}</span>{' '}
          <InfoTip term={active.term} />
        </h2>
        <div className="ranges" role="tablist" aria-label="Lab tools">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={t.id === tab}
              className={t.id === tab ? 'active' : ''}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      {tab === 'backtest' ? <BacktestPanel ticker={ticker} theme={theme} /> : <ForecastPanel ticker={ticker} theme={theme} />}
      <p className="note lab-disclaimer">Learning tool only, not financial advice. Past results don't predict the future.</p>
    </section>
  )
}
