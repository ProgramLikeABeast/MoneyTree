from openbb import obb
obb.user.preferences.output_type = "dataframe"

data = obb.equity.fundamental.metrics(
"AAPL,MSFT",
provider="yfinance"
)
print(data)