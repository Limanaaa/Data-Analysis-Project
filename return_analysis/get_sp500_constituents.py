import pandas as pd
from config import db, TARGET_YEAR


def get_sp500_constituents(year: int) -> pd.DataFrame:
    as_of_date = f"{year}-12-31"

    sql = f"""
    select distinct
        h.gvkey,
        h.iid,
        h.gvkeyx,
        h.from,
        h.thru,
        s.tic
    from comp.idxcst_his h
    left join comp.security s
        on h.gvkey = s.gvkey
       and h.iid = s.iid
    where h.gvkeyx = '000003'
      and h.from <= '{as_of_date}'
      and (h.thru is null or h.thru >= '{as_of_date}')
    order by h.gvkey, h.iid
    """

    df = db.raw_sql(sql, date_cols=["from", "thru"])

    # 保留每个 gvkey 的第一条记录（即 iid 最小）
    df = df.sort_values(["gvkey", "iid"]).drop_duplicates(subset=["gvkey"], keep="first")

    # 再按 ticker 排序，方便看
    df = df.sort_values(["tic", "gvkey"]).reset_index(drop=True)

    return df


if __name__ == "__main__":
    sp500 = get_sp500_constituents(TARGET_YEAR)

    print(sp500.head(20))
    print("Number of rows:", len(sp500))
    print("Number of unique gvkey:", sp500["gvkey"].nunique())
    print("Number of unique tic:", sp500["tic"].nunique())

    sp500.to_csv(f"sp500_constituents_{TARGET_YEAR}.csv", index=False)