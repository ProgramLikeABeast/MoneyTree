from openbb import obb
obb.user.preferences.output_type = "dataframe"


# build stock screeners
print("Create an overview screener based on a list of stocks using the default view:")
data = obb.equity.compare.groups(
    group="industry",
    metric="valuation",
    provider="finviz"
)
print(data)

print("Create a screener that returns the top gainers from the technology sector based on a preset sectors:")
data = obb.equity.compare.groups(
    group="technology",
    metric="performance",
    provider="finviz"
)
print(data)

print("Create a screener that presents an overview grouped by sectors aggregated:")
data = obb.equity.compare.groups(
    group="sector",
    metric="performance",
    provider="finviz"
)
print(data)