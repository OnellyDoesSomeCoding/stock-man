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
  paperTrading: {
    title: 'Paper trading',
    text: 'Practice buying and selling with fake money (you start with 100,000 THB). Trades use the real latest price, so you can learn how gains and losses work without risking anything.',
  },
  shares: {
    title: 'Shares',
    text: 'Small pieces of a company. Owning 100 shares of PTT means you own 100 tiny pieces; their total value moves with the share price.',
  },
  cash: { title: 'Cash', text: 'Fake money not spent on stocks yet. Buying uses cash; selling gives it back.' },
  avgCost: {
    title: 'Average cost',
    text: 'The average price you paid per share. Buy 100 at 10 and 100 at 20 = average cost 15. Selling does not change it.',
  },
  marketValue: {
    title: 'Value',
    text: 'What your shares are worth right now: shares × current price.',
  },
  profitLoss: {
    title: 'Profit / loss',
    text: 'Value now minus what you paid. "Unrealized" (on paper) while you still own the shares: it can still change. It becomes "realized" (locked in) when you sell.',
  },
  totalValue: {
    title: 'Total value',
    text: 'Cash + the current value of all your shares. Compare it with the 100,000 THB you started with to see how you are doing.',
  },
  backtest: {
    title: 'Backtest',
    text: 'Testing a trading rule on past prices: "if I had followed this rule, what would have happened?" Good past results do not promise good future results.',
  },
  buyAndHold: {
    title: 'Buy and hold',
    text: 'The simplest plan: buy on the first day and never sell. Any clever rule should beat this, or it is not worth the effort and fees.',
  },
  maxDrawdown: {
    title: 'Biggest drop',
    text: 'The largest fall from a previous high, e.g. 100,000 down to 70,000 = 30%. Shows how painful the worst stretch would have felt.',
  },
  winRate: {
    title: 'Win rate',
    text: 'Of the completed buy-then-sell rounds, the share that made money. A low win rate can still profit if the wins are big, and vice versa.',
  },
  brokerFee: {
    title: 'Broker fee',
    text: 'A small charge on every buy and sell (here 0.15%, typical for Thai online brokers). Rules that trade often lose a lot to fees.',
  },
  timeInMarket: {
    title: 'Time in market',
    text: 'The share of days the rule owned the stock. The rest of the time the money sat in cash.',
  },
  prediction: {
    title: 'Prediction experiment',
    text: 'Simple models guess the price a few days ahead. Each is tested on past days it had not seen yet, then compared with the laziest guess: "the price will not change".',
  },
  avgMiss: {
    title: 'Average miss',
    text: 'On average, how far the guess was from the real price, in baht and in %. Smaller is better.',
  },
  vsNaive: {
    title: 'vs "Tomorrow = today"',
    text: 'How much bigger (+) or smaller (-) the average miss was than just guessing "no change". Below 0% would mean the model beat the lazy guess.',
  },
  direction: {
    title: 'Direction right',
    text: 'How often the model correctly guessed up or down (days with no change are skipped). Compare it with always guessing the more common direction, not with 50%.',
  },
  outlook: {
    title: 'Typical range',
    text: 'Not a prediction: it shows how far the price usually moved over this many days in the past, applied to today\'s price. 8 times out of 10 it stayed inside this range.',
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
