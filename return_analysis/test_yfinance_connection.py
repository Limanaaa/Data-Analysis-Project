import yfinance as yf

# choose a test stock
ticker = "AAPL"

# download historical data
data = yf.download(ticker, start="2020-01-01", end="2020-12-31")

# print first few rows
print(data.head())

# check if data downloaded successfully
if data.empty:
    print("Download failed")
else:
    print("yfinance connection successful")