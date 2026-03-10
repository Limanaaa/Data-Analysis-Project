from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Union

import pandas as pd


def load_sentiment_portfolios(
    folder: Union[str, Path] = "data/sentiment_portfolios"
) -> pd.DataFrame:
    """
    Load all sentiment portfolio JSON files from a folder.

    Expected file naming convention:
        YYYY_long.json
        YYYY_short.json

    Expected JSON structure:
        [
            ["AAPL", "2019-01-30"],
            ["MSFT", "2019-01-31"]
        ]

    Returns
    -------
    pd.DataFrame
        Columns:
            - year: int
            - side: str ("long" or "short")
            - ticker: str
            - filing_date: datetime64[ns]
            - source_file: str
    """
    folder = Path(folder)

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")

    rows = []

    for file in sorted(folder.glob("*.json")):
        match = re.fullmatch(r"(\d{4})_(long|short)\.json", file.name)
        if not match:
            print(f"[WARNING] Skipping file with unexpected name format: {file.name}")
            continue

        year = int(match.group(1))
        side = match.group(2)

        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"{file.name} must contain a list.")

        for i, item in enumerate(data):
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError(
                    f"{file.name} row {i} must be a list of length 2: [ticker, filing_date]"
                )

            ticker, filing_date = item

            if not isinstance(ticker, str):
                raise ValueError(f"{file.name} row {i}: ticker must be a string.")

            if not isinstance(filing_date, str):
                raise ValueError(f"{file.name} row {i}: filing_date must be a string.")

            rows.append(
                {
                    "year": year,
                    "side": side,
                    "ticker": ticker.upper().strip(),
                    "filing_date": pd.to_datetime(filing_date),
                    "source_file": file.name,
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError(f"No valid portfolio data found in folder: {folder}")

    # Basic cleaning
    df = df.sort_values(["year", "side", "filing_date", "ticker"]).reset_index(drop=True)

    # Check for duplicates within the same year / side / ticker
    dup_mask = df.duplicated(subset=["year", "side", "ticker"], keep=False)
    if dup_mask.any():
        dup_df = df.loc[dup_mask, ["year", "side", "ticker", "source_file"]]
        raise ValueError(
            "Duplicate tickers found within the same year/side combination:\n"
            f"{dup_df.to_string(index=False)}"
        )

    return df


if __name__ == "__main__":
    # Adjust this path if needed depending on where you run the script from
    folder_path = Path("../data/sentiment_portfolios")

    print("=== Testing load_sentiment_portfolios ===")
    df = load_sentiment_portfolios(folder_path)

    print("\nLoaded DataFrame:")
    print(df)

    print("\nDataFrame info:")
    print(df.info())

    print("\nUnique years:")
    print(sorted(df["year"].unique().tolist()))

    print("\nUnique sides:")
    print(sorted(df["side"].unique().tolist()))

    print("\nUnique tickers:")
    print(sorted(df["ticker"].unique().tolist()))

    print("\nCounts by year and side:")
    print(df.groupby(["year", "side"]).size())

    print("\nMin / Max filing date:")
    print(df["filing_date"].min(), "->", df["filing_date"].max())