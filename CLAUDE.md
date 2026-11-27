# Stockman: Gold AI Bot (XAUUSD on MT5)

Stockman is a gold day-trading bot. The repo was reset from the earlier stock-analysis site; ignore anything left over from that.

## About me
- I have ZERO finance/trading knowledge. Explain any trading term in plain words the first time it appears.
- Keep answers short: bullet points or diagrams over paragraphs.
- My friend Jay owns the plan; I build it. His Claude Doc "Gold AI Bot Plan" is the single source of truth. If this file and the doc disagree, ask me.

## Rules for you (Claude)
- NEVER run `git commit` or `git push` unless I explicitly say so.
- NEVER place orders on a live (real-money) account. Demo account only, and only from Phase 4.
- Secrets (MT5 login, Discord webhook) go in `.env`, never in code. `.env` must be in `.gitignore`.
- Ask before adding big dependencies or changing the stack.
- One change at a time; after each step, tell me how to run/test it.

## Goal
A gold day-trading bot that makes more than it loses after spread and fees, proven on historical data and on demo before any real money.
Realistic good result: +0.1R to +0.3R per trade on average (R = the amount risked on one trade).

## Pass/fail gates (backtest): never change after seeing results
| Measure | Minimum |
|---|---|
| Avg result per trade | > +0.1R after costs |
| Win rate at 2R target | > 38% |
| Profit factor (wins ÷ losses) | > 1.3 |
| Trades tested | 200+ backtest, 50+ demo |
| Max drawdown | < 15% at 1% risk |
| At 2× costs | still profitable |

## Trading rules v1: trend pullback, 2R (all numbers are first guesses for the backtest)
1. Filters (all must pass):
   - New trades only 14:00–23:30 Thailand time (winter; 1h earlier Mar–Oct)
   - No trades 15 min before to 30 min after high-impact USD news (CPI, NFP, FOMC, PCE, GDP)
   - Spread ≤ 1.5× normal for that hour
   - Max 3 trades/day; stop after 2 losses; max 1 open trade; no new trades after 22:00 Friday
2. Trend (4H): EMA50 > EMA200, close > EMA50, ADX(14) > 20 → buy only. Mirror → sell only. Else no trade.
3. Entry (15m, buy example; sell is mirror):
   - Candle low within 0.3×ATR(14) of EMA20
   - RSI(14) dips below 40, then closes back above 40
   - Green candle closes above previous candle's high
   - Enter at NEXT candle's open, never on an unfinished candle
4. Stop: below lowest low of last 5 candles − 0.2×ATR; min 1×ATR, max 2.5×ATR (bigger = skip). Target: 2R.
   Skip if yesterday's high/low, last 4H swing, or a round number (3,500 / 3,550…) is closer than 2R.
5. Management: +1R → stop to breakeven; 16 candles without +1R → close; news in 30 min → close/tighten; 01:00 Thailand time → close all.
6. Test 3 exit versions on out-of-sample data: A fixed 2R, B breakeven at +1R, C half off at +1R, rest to 3R.
Every decision (including skips) is logged with its reason.

## Risk
- lot = (equity × risk%) / ((stop distance / tick size) × tick value), rounded DOWN to lot step
- Read tick value/size, min lot, lot step, contract size from MT5 `symbol_info`. Never hard-code.
- If min lot risks more than the limit → skip the trade.
- Limits: 1% per trade (0.5% first live month); day −2R or 2 losses → stop; week −5R → pause; drawdown −10% → stop + re-backtest; −15% → back to demo.
- Kill switch: one command closes all Stockman trades and stops new ones.

## Stack
- Windows only (MetaTrader5 Python package needs Windows + MT5 open and logged in)
- Python 3.11+, MetaTrader5, pandas, numpy, SQLite; scikit-learn + LightGBM in Phase 5
- Discord webhook for messages
- Python package name: `stockman`; ONE config file with a version number; every backtest result is saved with its config version
- KEY RULE: backtest and live bot run the EXACT same strategy code

## Modules by phase
| Phase | Modules |
|---|---|
| 1 | Data feed (M1/M15/H4 candles, tick, spread, account + symbol info; save history to files), news calendar (UTC → Thai time), indicators (EMA, RSI, ATR, ADX with Wilder smoothing, checked vs MT5) |
| 2 | Strategy (filters → trend → entry → stop/target, returns decision + reasons), backtester (candle by candle, with spread/commission/slippage), risk |
| 3 | Notifier (Discord templates), journal (SQLite), reporter (daily/weekly, live vs backtest), watchdog (heartbeat, alerts) |
| 4 | Execution on DEMO (orders with SL/TP, check fills, retry once), trade manager |
| 5 | AI scorer: probability a setup hits +2R before −1R; only kept if it beats plain rules out-of-sample after costs |
| 6 | Real money only after every gate passes (decided by Jay and me, not you) |
If Gate 2 (backtest) fails: that's a normal result. Try the next idea (London breakout, stop-hunt reversal, volatility squeeze) through the same gates.
(Gate details and Phase 3b "JARVIS assistant" are in Jay's doc. Ask me if you need them.)

## Testing honestly (non-negotiable)
1. No future data: use finished candles only (a 4H candle counts only after it closes)
2. Real fills: next candle open; buys at ask, sells at bid; sell stops trigger on ask
3. Real costs: real spread per hour + commission + 0.1–0.3 slippage; re-run at 2× costs
4. Stop and target in same candle → count as loss (or check M1)
5. Split by time, never shuffle: tune on oldest 60%, check next 20%, newest 20% locked until the very end
6. Walk-forward (tune 12 months, test next 3, slide by 3)
7. Few knobs: EMA 20/50/200, RSI 14, ATR 14, ADX 14 fixed; tune max 3 settings; nearby values must also work
8. Log every version tried
9. Slice results by year, month, hour, buy/sell, calm/wild days
10. Parity: live alert signals must match backtester signals for the same day
11. Demo avg R ≥ half of backtest avg R over 50+ trades

## Discord messages
- Sender name: "Stockman". Short Thai with common English trading words. Every message must contain a number or a time ("running, no signal" alone is banned).
- 08:00 daily report · 13:45 & 19:45 briefing (trend, ADX, spread, news countdown, waiting zone, readiness x/5) · "get ready" at 4/5 with trigger price · entry (side, entry, SL, TP, lot, risk in baht and %) · +1R manage · exits with reason and result · Sunday 20:00 weekly report · problem alerts anytime
- Send only when the bot's state changes (no spam)

## Known traps
- TIME: MT5 server time is usually GMT+2/+3. Measure the offset from the live tick time, store everything in UTC, convert to Thai time only for messages. Use real time zones (London, New York), never fixed offsets.
- Indicators must match MT5 values (compare 20 values; 200+ candles of warm-up).
- Save history early; brokers keep only a few years of M15. Check for gaps.
- Don't use volume (it's tick count, not real volume).
- Alert if the news calendar is empty for the week.
- Symbol name and contract size differ by broker (XAUUSD / XAUUSDm / GOLD; 100 oz or 1 oz).
- Check the broker's minimum stop distance before sending an order.
- On restart, read open positions by Stockman's magic number (a fixed ID tag on all its orders); always send SL/TP with the order.

## Open decisions (don't assume, ask me)
Broker/account type · where it runs (PC or Windows VPS) · first live account size · who answers alerts · news feed source · final gate numbers