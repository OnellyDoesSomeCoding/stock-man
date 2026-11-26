// Plain-language explanations used by every "?" tooltip. One place to edit the wording.

export const GLOSSARY = {
  ticker: {
    title: 'Ticker',
    text: 'Short code for a stock. PTT.BK = PTT on the Stock Exchange of Thailand (.BK = Bangkok).',
  },
  price: {
    title: 'Price',
    text: 'What one share cost in the most recent trade. Free data can be about 15 minutes late.',
  },
  change: {
    title: 'Change',
    text: "How far the price moved since the previous day's close, in baht and in percent. Green = up, red = down.",
  },
  previousClose: {
    title: 'Previous close',
    text: "The last price of the previous trading day. Today's change is measured from this number.",
  },
  marketCap: {
    title: 'Market cap',
    text: 'Price × number of shares = what the whole company is worth on the stock market. B = billion, T = trillion.',
  },
  pe: {
    title: 'P/E ratio',
    text: 'Price ÷ yearly profit per share. Roughly: how many baht you pay for each 1 baht the company earns per year. Higher often means investors expect growth, or the stock is expensive. Compare it with similar companies.',
    missing: 'Not available for this stock, often because the company made a loss (no profit) last year.',
  },
  candle: {
    title: 'Candle',
    text: "One trading day: its open, high, low and close prices. Green = closed higher than it opened, red = lower.",
  },
  movingAverage: {
    title: 'Moving average (MA)',
    text: 'The average closing price over the last N trading days, drawn as a smooth line. It hides day-to-day noise so the trend is easier to see. Price above the line = it has been rising lately; below = falling. Short lines (MA 20) react fast, long ones (MA 200) show the big picture. It describes the past; it does not predict.',
  },
  rsi: {
    title: 'RSI (Relative Strength Index)',
    text: 'A 0-100 score comparing the size of recent up-days with recent down-days (last 14 days). Above 70 = rose fast, maybe "overbought" (could cool down). Below 30 = fell fast, maybe "oversold" (could bounce). Prices can stay above 70 or below 30 for a long time: it describes the past, it does not predict.',
  },
  percentChange: {
    title: '% change (compare view)',
    text: 'How much the price went up or down compared with the first day shown. +10% means 1,000 THB of this stock on that first day would be worth 1,100 THB now. Using % instead of baht makes a 37-baht stock and a 50-baht stock fair to compare. Counts price moves only, not dividends (cash some companies pay their shareholders).',
  },
  watchlist: {
    title: 'Watchlist',
    text: "Your own list of stocks to keep an eye on, with each one's latest price and today's change. Click a row to open its chart. It is saved by the backend, so it stays after you close the browser.",
  },
  open: { title: 'Open', text: 'Price of the first trade that day.' },
  high: { title: 'High', text: 'Highest price anyone paid that day.' },
  low: { title: 'Low', text: 'Lowest price anyone paid that day.' },
  close: { title: 'Close', text: "Price of the last trade that day. This is the 'price' people usually quote." },
  volume: {
    title: 'Volume',
    text: 'Number of shares bought and sold that day. A big number means a busy day. M = million.',
  },
}
