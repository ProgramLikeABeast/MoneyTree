"""Regular intraday VWAP reconstruction from OHLCV bars."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def add_regular_vwap(
    frame: pd.DataFrame,
    *,
    group_cols: Sequence[str] = ("symbol", "trade_date"),
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    output_col: str = "regular_vwap",
) -> pd.DataFrame:
    """Add cumulative regular VWAP using typical price and volume."""

    required = set(group_cols) | {high_col, low_col, close_col, volume_col}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required VWAP columns: {missing}")

    result = frame.copy()
    typical_price = (result[high_col] + result[low_col] + result[close_col]) / 3
    price_volume = typical_price * result[volume_col]

    group_keys = [result[col] for col in group_cols]
    cumulative_price_volume = price_volume.groupby(group_keys, sort=False).cumsum()
    cumulative_volume = result[volume_col].groupby(group_keys, sort=False).cumsum()

    result[output_col] = cumulative_price_volume / cumulative_volume.where(cumulative_volume != 0)
    return result
