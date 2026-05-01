import yfinance as yf

data = yf.download("ES=F", period="3mo")
arr = data.to_numpy()
print(arr)