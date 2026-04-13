import wrds
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import config


def _clean_ret_value(x) -> Optional[float]:
    """
    Convert CRSP return field to float.
    CRSP ret may contain non-numeric codes such as 'B', 'C', etc.
    Return None for invalid values.
    """
    if pd.isna(x):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def get_holding_period_return(
    db: wrds.Connection,
    ticker: str,
    investment_date: str,
    holding_days: int
) -> Dict[str, Any]:
    """
    Calculate stock cumulative return from a given investment date for a given
    number of trading days using WRDS CRSP daily stock file.

    Parameters
    ----------
    db : wrds.Connection
        Active WRDS connection.
    ticker : str
        Stock ticker, e.g. 'AAPL'.
    investment_date : str
        Investment start date in 'YYYY-MM-DD' format.
    holding_days : int
        Number of trading days to hold.

    Returns
    -------
    dict
        {
            'ticker': str,
            'input_investment_date': str,
            'actual_start_date': str or None,
            'end_date': str or None,
            'holding_days_requested': int,
            'holding_days_used': int,
            'permno': int or None,
            'return': float or None
        }

    Notes
    -----
    1. This function aligns the start date to the first available trading date
       on or after investment_date.
    2. This simplified version uses CRSP `ret` only.
    3. holding_days means trading days, not calendar days.
    """
    if holding_days <= 0:
        raise ValueError("holding_days must be a positive integer.")

    investment_date = pd.Timestamp(investment_date).strftime("%Y-%m-%d")
    ticker = str(ticker).upper().strip()

    # Step 1: find the valid permno for this ticker around the investment date
    permno_sql = f"""
        SELECT permno, ticker, namedt, nameenddt
        FROM crsp.stocknames
        WHERE UPPER(ticker) = '{ticker}'
          AND namedt <= '{investment_date}'
          AND nameenddt >= '{investment_date}'
        ORDER BY namedt DESC
        LIMIT 1
    """
    permno_df = db.raw_sql(permno_sql)

    if permno_df.empty:
        # fallback: sometimes ticker-date match fails because of naming window issues
        permno_sql_fallback = f"""
            SELECT permno, ticker, namedt, nameenddt
            FROM crsp.stocknames
            WHERE UPPER(ticker) = '{ticker}'
            ORDER BY nameenddt DESC, namedt DESC
            LIMIT 5
        """
        fallback_df = db.raw_sql(permno_sql_fallback)

        if fallback_df.empty:
            return {
                "ticker": ticker,
                "input_investment_date": investment_date,
                "actual_start_date": None,
                "end_date": None,
                "holding_days_requested": holding_days,
                "holding_days_used": 0,
                "permno": None,
                "return": None
            }

        permno = int(fallback_df.iloc[0]["permno"])
    else:
        permno = int(permno_df.iloc[0]["permno"])

    # Step 2: get enough daily data after investment_date
    returns_sql = f"""
        SELECT date, ret
        FROM crsp.dsf
        WHERE permno = {permno}
          AND date >= '{investment_date}'
        ORDER BY date ASC
        LIMIT {holding_days + 30}
    """
    ret_df = db.raw_sql(returns_sql, date_cols=["date"])

    if ret_df.empty:
        return {
            "ticker": ticker,
            "input_investment_date": investment_date,
            "actual_start_date": None,
            "end_date": None,
            "holding_days_requested": holding_days,
            "holding_days_used": 0,
            "permno": permno,
            "return": None
        }

    # Step 3: clean returns
    ret_df["ret_clean"] = ret_df["ret"].apply(_clean_ret_value)
    ret_df["combined_ret"] = ret_df["ret_clean"]

    # Keep only rows with usable return data
    usable = ret_df[ret_df["combined_ret"].notna()].copy()

    if usable.empty:
        return {
            "ticker": ticker,
            "input_investment_date": investment_date,
            "actual_start_date": None,
            "end_date": None,
            "holding_days_requested": holding_days,
            "holding_days_used": 0,
            "permno": permno,
            "return": None
        }

    # Step 4: take first holding_days trading observations
    usable = usable.iloc[:holding_days].copy()

    if usable.empty:
        return {
            "ticker": ticker,
            "input_investment_date": investment_date,
            "actual_start_date": None,
            "end_date": None,
            "holding_days_requested": holding_days,
            "holding_days_used": 0,
            "permno": permno,
            "return": None
        }

    cumulative_return = np.prod(1.0 + usable["combined_ret"].values) - 1.0

    return {
        "ticker": ticker,
        "input_investment_date": investment_date,
        "actual_start_date": usable["date"].iloc[0].strftime("%Y-%m-%d"),
        "end_date": usable["date"].iloc[-1].strftime("%Y-%m-%d"),
        "holding_days_requested": holding_days,
        "holding_days_used": int(len(usable)),
        "permno": permno,
        "return": float(cumulative_return)
    }


def batch_get_holding_period_returns(
    db: wrds.Connection,
    events_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate holding period returns for a batch of events.

    Required columns in events_df:
    - ticker
    - investment_date
    - holding_days
    """
    required_cols = ["ticker", "investment_date", "holding_days"]
    missing_cols = [col for col in required_cols if col not in events_df.columns]
    if missing_cols:
        raise ValueError(f"events_df is missing required columns: {missing_cols}")

    results = []

    for _, row in events_df.iterrows():
        result = get_holding_period_return(
            db=db,
            ticker=row["ticker"],
            investment_date=row["investment_date"],
            holding_days=int(row["holding_days"])
        )
        results.append(result)

    return pd.DataFrame(results)


def batch_get_simple_price_returns(
    db: wrds.Connection,
    events_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Batch version of simple price return calculation.

    For each row in events_df, calculate:
        simple_price_return = end_price / start_price - 1

    Required columns in events_df:
    - ticker
    - investment_date
    - holding_days
    """
    required_cols = ["ticker", "investment_date", "holding_days"]
    missing_cols = [col for col in required_cols if col not in events_df.columns]
    if missing_cols:
        raise ValueError(f"events_df is missing required columns: {missing_cols}")

    results = []

    for _, row in events_df.iterrows():
        ticker = str(row["ticker"]).upper().strip()
        investment_date = pd.Timestamp(row["investment_date"]).strftime("%Y-%m-%d")
        holding_days = int(row["holding_days"])

        if holding_days <= 0:
            results.append({
                "ticker": ticker,
                "input_investment_date": investment_date,
                "actual_start_date": None,
                "end_date": None,
                "holding_days_requested": holding_days,
                "holding_days_used": 0,
                "permno": None,
                "start_price": None,
                "end_price": None,
                "simple_price_return": None
            })
            continue

        # Step 1: map ticker to permno
        permno_sql = f"""
            SELECT permno, ticker, namedt, nameenddt
            FROM crsp.stocknames
            WHERE UPPER(ticker) = '{ticker}'
              AND namedt <= '{investment_date}'
              AND nameenddt >= '{investment_date}'
            ORDER BY namedt DESC
            LIMIT 1
        """
        permno_df = db.raw_sql(permno_sql)

        if permno_df.empty:
            permno_sql_fallback = f"""
                SELECT permno, ticker, namedt, nameenddt
                FROM crsp.stocknames
                WHERE UPPER(ticker) = '{ticker}'
                ORDER BY nameenddt DESC, namedt DESC
                LIMIT 5
            """
            fallback_df = db.raw_sql(permno_sql_fallback)

            if fallback_df.empty:
                results.append({
                    "ticker": ticker,
                    "input_investment_date": investment_date,
                    "actual_start_date": None,
                    "end_date": None,
                    "holding_days_requested": holding_days,
                    "holding_days_used": 0,
                    "permno": None,
                    "start_price": None,
                    "end_price": None,
                    "simple_price_return": None
                })
                continue

            permno = int(fallback_df.iloc[0]["permno"])
        else:
            permno = int(permno_df.iloc[0]["permno"])

        # Step 2: pull daily prices
        price_sql = f"""
            SELECT date, prc
            FROM crsp.dsf
            WHERE permno = {permno}
              AND date >= '{investment_date}'
            ORDER BY date ASC
            LIMIT {holding_days + 30}
        """
        price_df = db.raw_sql(price_sql, date_cols=["date"])

        if price_df.empty:
            results.append({
                "ticker": ticker,
                "input_investment_date": investment_date,
                "actual_start_date": None,
                "end_date": None,
                "holding_days_requested": holding_days,
                "holding_days_used": 0,
                "permno": permno,
                "start_price": None,
                "end_price": None,
                "simple_price_return": None
            })
            continue

        # Step 3: clean prices
        price_df["prc_clean"] = pd.to_numeric(price_df["prc"], errors="coerce").abs()
        usable = price_df[price_df["prc_clean"].notna()].copy()

        if usable.empty:
            results.append({
                "ticker": ticker,
                "input_investment_date": investment_date,
                "actual_start_date": None,
                "end_date": None,
                "holding_days_requested": holding_days,
                "holding_days_used": 0,
                "permno": permno,
                "start_price": None,
                "end_price": None,
                "simple_price_return": None
            })
            continue

        usable = usable.iloc[:holding_days].copy()

        if usable.empty:
            results.append({
                "ticker": ticker,
                "input_investment_date": investment_date,
                "actual_start_date": None,
                "end_date": None,
                "holding_days_requested": holding_days,
                "holding_days_used": 0,
                "permno": permno,
                "start_price": None,
                "end_price": None,
                "simple_price_return": None
            })
            continue

        start_price = float(usable["prc_clean"].iloc[0])
        end_price = float(usable["prc_clean"].iloc[-1])
        simple_return = None if start_price == 0 else end_price / start_price - 1.0

        results.append({
            "ticker": ticker,
            "input_investment_date": investment_date,
            "actual_start_date": usable["date"].iloc[0].strftime("%Y-%m-%d"),
            "end_date": usable["date"].iloc[-1].strftime("%Y-%m-%d"),
            "holding_days_requested": holding_days,
            "holding_days_used": int(len(usable)),
            "permno": permno,
            "start_price": start_price,
            "end_price": end_price,
            "simple_price_return": simple_return
        })

    return pd.DataFrame(results)



if __name__ == "__main__":
    db = config.db

    # single test
    # result = get_holding_period_return(
    #     db=db,
    #     ticker="AAPL",
    #     investment_date="2024-01-15",
    #     holding_days=63
    # )
    
    
    # print("Single result:")
    # print(result)

    

    # batch test
    events_df = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "NVDA"],
        "investment_date": ["2024-01-15", "2024-02-01", "2024-03-01"],
        "holding_days": [63, 63, 63]
    })
    if 'compound' in config.return_cal_list:
        print('\n=========compound=========')
        batch_result = batch_get_holding_period_returns(
            db=db,
            events_df=events_df
        )
        print("\nBatch results:")
        print(batch_result)

    if 'simple' in config.return_cal_list:
        print('\n=========simple=========')
        batch_result = batch_get_simple_price_returns(
        db=db,
        events_df=events_df
        )
        print("\nBatch results:")
        print(batch_result)