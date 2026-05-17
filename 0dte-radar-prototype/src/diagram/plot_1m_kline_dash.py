"""Beginner Dash example for displaying 1-minute K-line data."""

from __future__ import annotations

from dash import Dash, Input, Output, State, dcc, html
import plotly.graph_objects as go

from data.request_1m_kline import request_1m_regular_session


DEFAULT_TRADE_DATE = "2026-05-15"
DEFAULT_CODE = "US.QQQ"


def build_1m_kline_figure(trade_date: str, code: str) -> go.Figure:
    """Fetch one day of 1-minute K-line data and build a Plotly figure."""
    frame = request_1m_regular_session(
        trade_date=trade_date,
        code=code,
    )

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=frame["time_key"],
                open=frame["open"],
                high=frame["high"],
                low=frame["low"],
                close=frame["close"],
                name=f"{code} 1m K-line",
            )
        ]
    )

    fig.update_layout(
        title=f"{code} 1-Minute K-line - {trade_date}",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
    )

    return fig


def create_app() -> Dash:
    """Create a small Dash app that serves the K-line chart."""
    app = Dash(__name__)
    app.layout = html.Div(
        children=[
            html.H1("1-Minute K-line Viewer"),
            html.Div(
                children=[
                    html.Label("Trade date"),
                    dcc.Input(
                        id="trade-date-input",
                        type="text",
                        value=DEFAULT_TRADE_DATE,
                        placeholder="YYYY-MM-DD",
                    ),
                    html.Label("Code"),
                    dcc.Input(
                        id="code-input",
                        type="text",
                        value=DEFAULT_CODE,
                        placeholder="US.QQQ",
                    ),
                    html.Button("Draw", id="draw-button", n_clicks=0),
                ],
                style={"display": "flex", "gap": "12px", "alignItems": "center"},
            ),
            dcc.Graph(id="kline-chart"),
        ]
    )

    @app.callback(
        Output("kline-chart", "figure"),
        Input("draw-button", "n_clicks"),
        State("trade-date-input", "value"),
        State("code-input", "value"),
    )
    def draw_chart(_n_clicks: int, trade_date: str, code: str) -> go.Figure:
        return build_1m_kline_figure(trade_date=trade_date, code=code)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=8050, debug=True)
