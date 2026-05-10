from openbb import obb
obb.user.preferences.output_type = "dataframe"

data = obb.equity.price.historical(
    "QQQ", provider="yfinance",
    start_date="2026-04-30",
    end_date="2026-04-30",
    interval="15m")
print(data)