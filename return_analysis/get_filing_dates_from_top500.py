import pandas as pd
from config import db, TARGET_YEAR


def normalize_cik(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lstrip("0")
        .replace("", pd.NA)
    )


def load_top500(year: int) -> pd.DataFrame:
    file_path = f"top500_by_mktcap_{year}.csv"
    df = pd.read_csv(file_path, dtype={"permno": str, "permco": str, "ncusip": str})
    df["ticker"] = df["ticker"].astype(str).str.strip()
    df["row_id"] = range(len(df))
    return df


def load_local_sec10k_index(year: int) -> pd.DataFrame:
    file_path = f"sec10k_file_index_{year}.csv"
    df = pd.read_csv(file_path, dtype={"cik": str})
    df["cik_norm"] = normalize_cik(df["cik"])
    df["filing_date"] = pd.to_datetime(df["filing_date"], format="%Y%m%d", errors="coerce")
    return df


def get_security_link(top500: pd.DataFrame) -> pd.DataFrame:
    ticker_list = top500["ticker"].dropna().astype(str).unique().tolist()
    ticker_str = ",".join([f"'{x}'" for x in ticker_list])

    sql = f"""
    select
        tic,
        gvkey,
        iid,
        cusip
    from comp.security
    where tic in ({ticker_str})
    """

    security = db.raw_sql(sql)
    security["tic"] = security["tic"].astype(str).str.strip()

    # 每个 ticker 先保留第一条
    security = (
        security.sort_values(["tic", "gvkey", "iid"])
        .drop_duplicates(subset=["tic"], keep="first")
        .reset_index(drop=True)
    )
    return security


def get_company_link(security: pd.DataFrame) -> pd.DataFrame:
    gvkey_list = security["gvkey"].dropna().astype(str).unique().tolist()
    gvkey_str = ",".join([f"'{x}'" for x in gvkey_list])

    sql = f"""
    select
        gvkey,
        cik,
        conm
    from comp.company
    where gvkey in ({gvkey_str})
    """

    company = db.raw_sql(sql)
    company["gvkey"] = company["gvkey"].astype(str).str.strip()
    company["cik_norm"] = normalize_cik(company["cik"])
    return company


def build_filing_date_table(year: int) -> pd.DataFrame:
    top500 = load_top500(year)
    sec10k = load_local_sec10k_index(year)

    security = get_security_link(top500)
    company = get_company_link(security)

    # top500 ticker -> security.tic
    result = top500.merge(
        security.rename(columns={"tic": "ticker"}),
        on="ticker",
        how="left"
    )

    result["gvkey"] = result["gvkey"].astype(str).str.strip()

    # gvkey -> company -> cik
    result = result.merge(
        company[["gvkey", "cik", "cik_norm", "conm"]],
        on="gvkey",
        how="left"
    )

    # cik -> local sec10k file index
    result = result.merge(
        sec10k[["cik_norm", "filing_date", "form_type", "accession_number", "file_name", "file_path"]],
        on="cik_norm",
        how="left"
    )

    # 每个股票只保留一条
    result = (
        result.sort_values(["row_id", "filing_date"])
        .drop_duplicates(subset=["row_id"], keep="first")
        .reset_index(drop=True)
    )

    return result


if __name__ == "__main__":
    filing_df = build_filing_date_table(TARGET_YEAR)

    print(f"TARGET_YEAR = {TARGET_YEAR}")
    print(f"Number of rows: {len(filing_df)}")
    print(f"Number of non-missing gvkey: {filing_df['gvkey'].notna().sum()}")
    print(f"Number of non-missing cik: {filing_df['cik'].notna().sum()}")
    print(f"Number of non-missing filing dates: {filing_df['filing_date'].notna().sum()}")

    matched = filing_df[filing_df["filing_date"].notna()].copy()
    unmatched = filing_df[filing_df["filing_date"].isna()].copy()

    print("\nMatched sample:")
    print(
        matched[
            ["permno", "ticker", "gvkey", "cik", "filing_date", "form_type", "file_name"]
        ].head(20)
    )

    print("\nUnmatched sample:")
    print(
        unmatched[
            ["permno", "ticker", "gvkey", "cik", "conm"]
        ].head(20)
    )

    filing_df.to_csv(f"top500_filing_dates_{TARGET_YEAR}.csv", index=False)
    matched.to_csv(f"top500_filing_dates_matched_{TARGET_YEAR}.csv", index=False)
    unmatched.to_csv(f"top500_filing_dates_unmatched_{TARGET_YEAR}.csv", index=False)

    print(f"\nSaved: top500_filing_dates_{TARGET_YEAR}.csv")
    print(f"Saved: top500_filing_dates_matched_{TARGET_YEAR}.csv")
    print(f"Saved: top500_filing_dates_unmatched_{TARGET_YEAR}.csv")