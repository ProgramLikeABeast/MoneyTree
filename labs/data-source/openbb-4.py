import pandas as pd
import matplotlib.pyplot as plt
from openbb import obb
obb.user.preferences.output_type = "dataframe"

data = obb.derivatives.futures.curve(symbol="VX_EOD")
data["expiration"] = pd.to_datetime(data["expiration"])
print(data)
data = data.set_index("expiration")
data.plot(title="VX Futures Curve", marker="o")
plt.tight_layout()
plt.show()