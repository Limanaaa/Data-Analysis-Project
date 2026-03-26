import pandas as pd
from config import db, TARGET_YEAR


def get_top500_by_mktcap(year: int) -> pd.DataFrame:
    as_of_date = f"{year}-12-31"

    sql = f"""
    with last_trading_day as (
        select max(date) as trade_date
        from crsp.dsf
        where date <= '{as_of_date}'
    ),
    base as (
        select
            d.permno,
            d.permco,
            d.date,
            d.prc,
            d.shrout,
            abs(d.prc) * d.shrout as market_equity,
            n.ticker,
            n.comnam,
            n.shrcd,
            n.exchcd,
            n.ncusip
        from crsp.dsf d
        join last_trading_day t
            on d.date = t.trade_date
        left join crsp.stocknames n
            on d.permno = n.permno
           and n.namedt <= d.date
           and d.date <= n.nameenddt
        where n.shrcd in (10, 11)
          and n.exchcd in (1, 2, 3)
          and d.prc is not null
          and d.shrout is not null
    )
    select *
    from base
    order by market_equity desc
    limit 500
    """

    df = db.raw_sql(sql, date_cols=["date"])

    df = df.sort_values("market_equity", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)

    return df


if __name__ == "__main__":
    top500 = get_top500_by_mktcap(TARGET_YEAR)

    print(f"TARGET_YEAR = {TARGET_YEAR}")
    print(f"Number of rows: {len(top500)}")
    print(top500.head(20))

    output_path = f"top500_by_mktcap_{TARGET_YEAR}.csv"
    top500.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")