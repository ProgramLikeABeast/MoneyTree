import pandas as pd
from openbb import obb
obb.user.preferences.output_type = "dataframe"


expirations = [
    "2024-12",
    "2025-12",
    "2026-12",
    "2027-12",
    "2028-12",
    "2029-12",
    "2030-12"
]

contracts = {}
for expiration in expirations:
    df = obb.derivatives.futures.historical(
        symbol="BTC",
        expiration=expiration,
        start_date="2020-01-01",
        end_date="2022-12-31"
    )
    contracts[expiration] = df["close"]

historical = pd.concat(contracts, axis=1).dropna()
print(historical)
historical.iloc[-1].plot()