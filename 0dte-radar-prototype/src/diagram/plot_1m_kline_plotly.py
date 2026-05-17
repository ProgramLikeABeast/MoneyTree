"""Beginner Plotly example for displaying 1-minute K-line data."""

from __future__ import annotations

import plotly.graph_objects as go

from data.request_1m_kline import request_1m_regular_session


def plot_1m_kline() -> None:
    """Fetch one day of 1-minute K-line data and display it with Plotly."""
    frame = request_1m_regular_session(
        trade_date="2026-05-15",
        code="US.QQQ",
    )

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=frame["time_key"],
                open=frame["open"],
                high=frame["high"],
                low=frame["low"],
                close=frame["close"],
                name="US.QQQ 1m K-line",
            )
        ]
    )

    fig.update_layout(
        title="US.QQQ 1-Minute K-line - 2026-05-15",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
    )

    fig.show()


if __name__ == "__main__":
    plot_1m_kline()
