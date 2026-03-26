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

## return analysis

**IMMPORTANT!!!! go to config.py AND change username and psw for wrds**

`get_return.py` needs input as the following format:

```python

    events_df = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "NVDA"],
        "investment_date": ["2024-01-15", "2024-02-01", "2024-03-01"],
        "holding_days": [63, 63, 63]
    })

```

今天最终确认的思路是：

我们不再死磕严格的 S&P 500 成分股，也不再依赖 WRDS 里覆盖不完整的 SEC sample 表去找 10-K filing date。
新的主线是：

先用 WRDS 的 CRSP 数据，在 `TARGET_YEAR` 年末按市值选出前 500 只股票，作为样本池；
再用本地下载的 SEC 10-K 文件夹，从文件名里直接提取 `filing_date + cik`；
然后把股票池通过 `ticker -> gvkey -> cik` 连到本地 10-K 文件索引；
最后得到每只股票的 filing date，之后再去算 `[0,1]` 的最简单 sentiment proxy。

今天已经确认可行的核心代码有三块：

第一，`get_top500_by_mktcap.py`
作用：从 WRDS/CRSP 里取某年年末市值前 500 只股票，并导出 `top500_by_mktcap_{TARGET_YEAR}.csv`。
这一步已经跑通，而且结果合理。

第二，`inspect_sec10x_folder.py`
作用：扫描某个年份某个季度的本地 10-K 文件夹，从文件名提取
`filing_date / form_type / cik / accession_number`，生成 `sec10k_file_index_{TARGET_YEAR}.csv`。
这一步也已经验证成功，文件名解析完全没问题。

第三，`get_filing_dates_from_top500.py`
作用：读取 top500 股票池，先通过
`ticker -> comp.security -> gvkey -> comp.company -> cik`
再和本地 10-K 文件索引按 `cik` merge，得到 `filing_date`。
这一步已经跑通，2010 年 Q4 的测试结果也是合理的。

明天的任务很清楚：

第一，把 `2010–2024` 的 10-K 文件夹按统一结构放好，最好每年下面都有 `QTR1` 到 `QTR4`。

第二，把 `inspect_sec10x_folder.py` 升级成“全年扫描版”，让它自动扫描某一年四个季度，而不是只看一个季度。

第三，重新跑 `get_filing_dates_from_top500.py`，这样每年的 `filing_date` 覆盖率会明显提高。

第四，如果 filing date 这一步完整了，我们就进入下一步，直接写代码去算最简单的 sentiment proxy，也就是 filing 后 `[0,1]` 两个交易日累计收益。

但是我觉得其实可以把所有股票全都放进来处理，这样会快很多
