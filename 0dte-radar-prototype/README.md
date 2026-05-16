# 0DTE Radar Prototype

Phase 1 focuses on a minimal local data loop:

```text
Moomoo OpenD -> Python SDK -> SPY / QQQ quotes -> DuckDB -> Plotly
```

Current work should stay focused on connecting to OpenD, collecting `US.SPY` / `US.QQQ` quotes, replaying historical bars when the market is closed, saving `underlying_quotes`, and displaying a simple Plotly panel.
