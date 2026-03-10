from __future__ import annotations

import pandas as pd


def build_position_table(
    sentiment_df: pd.DataFrame,
    returns: pd.DataFrame,
    holding_days: int = 365,
) -> pd.DataFrame:
    """
    Convert sentiment portfolio entries into actual position events.

    Parameters
    ----------
    sentiment_df : pd.DataFrame
        Must contain:
            - year
            - side
            - ticker
            - filing_date
    returns : pd.DataFrame
        Daily stock return DataFrame.
        Index must be trading dates (DatetimeIndex).
        Columns must be tickers.
    holding_days : int, default 365
        Calendar-day holding period after formation.

    Returns
    -------
    pd.DataFrame
        Columns:
            - year
            - side
            - ticker
            - filing_date
            - formation_date
            - end_date
            - source_file (if available in input)
    """
    required_cols = {"year", "side", "ticker", "filing_date"}
    missing_cols = required_cols - set(sentiment_df.columns)
    if missing_cols:
        raise ValueError(f"sentiment_df is missing required columns: {missing_cols}")

    if not isinstance(returns.index, pd.DatetimeIndex):
        raise ValueError("returns.index must be a pandas DatetimeIndex.")

    if returns.empty:
        raise ValueError("returns DataFrame is empty.")

    trading_dates = returns.index.sort_values()
    available_tickers = set(returns.columns)

    position_rows = []

    for _, row in sentiment_df.iterrows():
        ticker = row["ticker"]
        filing_date = pd.to_datetime(row["filing_date"])

        # Check ticker exists in downloaded returns
        if ticker not in available_tickers:
            print(f"[WARNING] Skipping {ticker}: not found in returns columns.")
            continue

        # Find first trading day strictly after filing_date
        possible_dates = trading_dates[trading_dates > filing_date]
        if len(possible_dates) == 0:
            print(
                f"[WARNING] Skipping {ticker} ({filing_date.date()}): "
                "no trading day found after filing_date."
            )
            continue

        formation_date = possible_dates[0]

        # Hold for one year in calendar days
        target_end_date = formation_date + pd.Timedelta(days=holding_days)

        # Last available trading day on or before target_end_date
        valid_end_dates = trading_dates[trading_dates <= target_end_date]
        if len(valid_end_dates) == 0:
            print(
                f"[WARNING] Skipping {ticker} ({filing_date.date()}): "
                "no valid end date found."
            )
            continue

        end_date = valid_end_dates[-1]

        # Extra sanity check
        if formation_date > end_date:
            print(
                f"[WARNING] Skipping {ticker} ({filing_date.date()}): "
                f"formation_date {formation_date.date()} > end_date {end_date.date()}."
            )
            continue

        out_row = {
            "year": row["year"],
            "side": row["side"],
            "ticker": ticker,
            "filing_date": filing_date,
            "formation_date": formation_date,
            "end_date": end_date,
        }

        # Keep source_file if present
        if "source_file" in sentiment_df.columns:
            out_row["source_file"] = row["source_file"]

        position_rows.append(out_row)

    position_table = pd.DataFrame(position_rows)

    if position_table.empty:
        raise ValueError("No valid positions could be constructed.")

    position_table = position_table.sort_values(
        ["formation_date", "side", "ticker"]
    ).reset_index(drop=True)

    return position_table


if __name__ == "__main__":
    import yfinance as yf
    from pathlib import Path
    from load_sentiment_portfolios import load_sentiment_portfolios

    # 1. Load sentiment files
    sentiment_df = load_sentiment_portfolios(Path("../data/sentiment_portfolios"))

    print("=== sentiment_df ===")
    print(sentiment_df)

    # 2. Download prices from yfinance
    tickers = sorted(sentiment_df["ticker"].unique().tolist())
    start_date = (sentiment_df["filing_date"].min() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = (sentiment_df["filing_date"].max() + pd.Timedelta(days=400)).strftime("%Y-%m-%d")

    prices = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        auto_adjust=False,
        progress=False,
    )["Adj Close"]

    # If only one ticker, yfinance may return a Series
    if isinstance(prices, pd.Series):
        prices = prices.to_frame()

    returns = prices.pct_change().dropna(how="all")

    print("\n=== returns head ===")
    print(returns.head())

    # 3. Build position table
    position_table = build_position_table(sentiment_df, returns)

    print("\n=== position_table ===")
    print(position_table)

    print("\n=== counts by side ===")
    print(position_table.groupby(["year", "side"]).size())