# Data Format Required for Portfolio Backtest

To run the portfolio backtest, I need the sentiment results in a simple JSON format.

## Files Needed

For **each year**, please provide **two JSON files**:

- `{year}_long.json` → firms with the **highest sentiment scores** (Top group)
- `{year}_short.json` → firms with the **lowest sentiment scores** (Bottom group)

Example:

```
2018_long.json
2018_short.json
2019_long.json
2019_short.json
```

## JSON Structure

Each file should contain a list of pairs:

```
[ticker, filing_date]
```

Example:

```json
[
  ["AAPL", "2019-02-01"],
  ["MSFT", "2019-01-30"],
  ["NVDA", "2019-02-15"]
]
```

Where:

- **ticker** = stock ticker
- **filing_date** = the **10-K release date** (format: `YYYY-MM-DD`)

## Portfolio Definition

- **Long portfolio** = firms with the **highest sentiment scores**
- **Short portfolio** = firms with the **lowest sentiment scores**

Suggested size:

```
Top 20 firms → long
Bottom 20 firms → short
```

## Notes

- Please use **standard US tickers**.
- Date format must be **YYYY-MM-DD**.
- No duplicate tickers within the same file.

This format will allow the backtest code to directly build portfolios and compute returns.
