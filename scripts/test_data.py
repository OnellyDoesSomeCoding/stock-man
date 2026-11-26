"""Step 0: check that yfinance can fetch Thai (SET) stock prices.

Fetches 1 year of daily prices for PTT.BK, prints the last 5 days,
explains each column, and saves a price chart to ptt_chart.png.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to a file, no pop-up window needed
import matplotlib.pyplot as plt
import yfinance as yf

TICKER = "PTT.BK"  # ".BK" = listed on the Stock Exchange of Thailand (Bangkok)
OUTPUT = Path(__file__).resolve().parent.parent / "ptt_chart.png"

COLUMN_HELP = {
    "Open": "Price of the first trade that day (THB)",
    "High": "Highest price anyone paid that day (THB)",
    "Low": "Lowest price anyone paid that day (THB)",
    "Close": "Price of the last trade that day (THB) - the 'price' people usually quote",
    "Volume": "Number of shares bought/sold that day (busy day = big number)",
}


def main() -> int:
    print(f"Fetching 1 year of daily prices for {TICKER} ...")
    df = yf.Ticker(TICKER).history(period="1y", interval="1d", auto_adjust=False)

    if df.empty:
        print(f"ERROR: yfinance returned no data for {TICKER}.")
        print("The data source may be down or the ticker format changed.")
        return 1

    df = df[list(COLUMN_HELP)]  # keep only the columns we explain
    print(f"Got {len(df)} trading days ({df.index[0]:%Y-%m-%d} to {df.index[-1]:%Y-%m-%d})\n")

    print("Last 5 trading days:")
    print(df.tail(5).round(2).to_string())

    print("\nWhat each column means:")
    print(f"  {'Date':<7} One row = one trading day (weekends/holidays are skipped)")
    for col, meaning in COLUMN_HELP.items():
        print(f"  {col:<7} {meaning}")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df["Close"], linewidth=1.5)
    ax.set_title(f"{TICKER} closing price - last 1 year")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (THB)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=120)
    print(f"\nChart saved to {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
