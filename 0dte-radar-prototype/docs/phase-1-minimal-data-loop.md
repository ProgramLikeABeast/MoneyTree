# Phase 1：最小可运行数据闭环

## 1. Goal

本阶段目标很简单：先把最小 real-time data loop 跑通。

```text
Moomoo OpenD → Python SDK → SPY / QQQ 实时价格 → Local storage → Plotly chart
```

Phase 1 不做期权链、不做 Greeks、不做交易信号，也不接自动交易。只验证一件事：

> Python 能稳定从 Moomoo OpenD 获取 SPY / QQQ 价格，并在本地持续保存和展示。

## 2. Scope

### In Scope

1. 启动并连接 Moomoo OpenD。
2. Python SDK 获取 `US.SPY` / `US.QQQ` quote。
3. 每 1-5 秒更新本地 quote buffer。
4. 每 2 分钟刷新 Plotly price panel。
5. 保存数据到 `underlying_quotes`。
6. 闭市时使用 historical bars replay，模拟时间流逝。

### Out of Scope

1. 期权链 discovery。
2. 期权 quote / snapshot。
3. VWAP / GWAP / 神掌指标。
4. Radar signal scoring。
5. 自动下单。
6. Cloud deployment。

## 3. Simple Architecture

```text
[Moomoo OpenD]
      ↓
[Moomoo Python SDK]
      ↓
[Quote Collector]
      ↓
[In-memory DataFrame / Buffer]
      ↓
[DuckDB: underlying_quotes]
      ↓
[Plotly Dashboard]
```

闭市时：

```text
[Historical Bars]
      ↓
[Replay Engine: 1 bar per N seconds]
      ↓
[Same Buffer / Same Plotly Panel / Same Storage]
```

关键原则：real-time mode 和 replay mode 尽量输出同一种 quote schema，这样 dashboard 和 storage 不需要关心数据来自哪里。

## 4. Data Schema

Phase 1 只需要一张表：`underlying_quotes`。

建议字段：

```text
symbol          text        # US.SPY / US.QQQ
timestamp       timestamp   # market data timestamp
bid             double
ask             double
last            double
open            double
high            double
low             double
close           double
volume          bigint
source          text        # moomoo_realtime / moomoo_history_replay
mode            text        # realtime / replay
received_at     timestamp   # local receive time
```

如果 Moomoo quote 里某些字段暂时拿不到，可以先存 `null`，但 `symbol`、`timestamp`、`last`、`source`、`mode`、`received_at` 必须稳定。

## 5. Implementation Plan

### Step 1：OpenD Ready

目标：确认本地 OpenD 可以被 Python 连接。

要做：

1. 启动 Moomoo OpenD。
2. 确认 host / port，例如：

   ```text
   host = 127.0.0.1
   port = 11111
   ```

3. 在 `.env` 或 config 中保存连接参数。
4. 写一个最小 connection test script。

完成标准：

- Python script 能成功 connect OpenD。
- 失败时能打印清楚错误，比如 OpenD 未启动、端口不对、权限不足。

### Step 2：Realtime Quote Collector

目标：获取 SPY / QQQ 实时 quote。

要做：

1. 使用 Moomoo Python SDK 创建 quote context。
2. 订阅或轮询：

   ```text
   US.SPY
   US.QQQ
   ```

3. 第一版可以优先 polling，每 1-5 秒请求一次 quote。
4. 每次 quote 转成统一 record。

建议先用 polling，因为更容易 debug。后续如果需要更低延迟，再切 subscription callback。

完成标准：

- 能连续打印 SPY / QQQ 的 `last` price。
- 运行 10-30 分钟不崩。

### Step 3：Local Buffer

目标：把最新 quote 存在本地内存里，给 Plotly 使用。

要做：

1. 使用 Pandas DataFrame 或简单 list buffer。
2. 每次 quote append 一行。
3. 只保留最近 N 小时数据，避免内存无限增长。
4. buffer 同时支持 realtime mode 和 replay mode。

建议：

```text
refresh_quote_interval = 1-5 seconds
max_buffer_hours = 6.5
```

完成标准：

- buffer 中能看到 SPY / QQQ 按时间增长。
- 重复 quote 不会导致图表明显异常。

### Step 4：Market Closed Replay Mode

目标：闭市时也能开发和测试 dashboard。

要做：

1. 判断当前是否 market open。
2. 如果 market closed，加载最近一个交易日的 historical bars。
3. 用 ticker / timer 模拟时间流逝：

   ```text
   every 1-5 seconds:
       emit next historical bar as fake quote
   ```

4. replay 输出和 realtime quote 使用同一个 schema。
5. `source = moomoo_history_replay`，`mode = replay`。

完成标准：

- 闭市时也能看到 SPY / QQQ price line moving。
- Plotly dashboard 不需要知道当前是 realtime 还是 replay。

### Step 5：Persist `underlying_quotes`

目标：把 quote 数据落地，方便盘后 replay 和 debug。

要做：

1. 使用 DuckDB 创建 `underlying_quotes`。
2. 每次 quote append 到表中。
3. 可以先简单直接 insert，不需要复杂 batch。
4. 如果写入频率太高，再改成 batch insert。

建议第一版：

```text
insert every quote immediately
or
flush every 10-30 seconds
```

完成标准：

- DuckDB 中能查到 SPY / QQQ quote history。
- 停止程序后，数据仍然存在。

### Step 6：Plotly Price Panel

目标：展示 SPY / QQQ 实时价格曲线。

要做：

1. 使用 Plotly 画两条 line：
   - SPY last price
   - QQQ last price
2. Dashboard 每 2 分钟刷新一次。
3. 页面显示：
   - 当前 mode：`realtime` / `replay`
   - latest timestamp
   - latest SPY / QQQ last price
   - data source
4. 第一版可以用 Dash，也可以先生成本地 HTML。

建议：

- 如果想快速验证，用 Plotly HTML。
- 如果想持续刷新，用 Dash。

完成标准：

- 能稳定显示 SPY / QQQ price curves。
- 价格曲线会随着 collector 更新。

## 6. Suggested File Layout

可以保持简单，不需要过早拆太细。

```text
0dte-radar-prototype/
  src/
    config.py
    data/
      moomoo_client.py
      quote_collector.py
      historical_replay.py
      storage.py
    dashboard/
      price_panel.py
  data/
    duckdb/
      odte_radar.duckdb
```

每个文件职责：

```text
config.py              读取 host / port / symbols / refresh interval
moomoo_client.py       创建 OpenD quote context
quote_collector.py     realtime quote polling loop
historical_replay.py   market closed replay mode
storage.py             DuckDB underlying_quotes insert/query
price_panel.py         Plotly / Dash chart
```

## 7. Config Draft

可以先用简单 `.env`：

```text
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
SYMBOLS=US.SPY,US.QQQ
QUOTE_INTERVAL_SECONDS=2
PLOT_REFRESH_SECONDS=120
DATA_MODE=auto
DUCKDB_PATH=data/duckdb/odte_radar.duckdb
```

`DATA_MODE` 建议支持：

```text
auto       market open 用 realtime，closed 用 replay
realtime   强制 realtime
replay     强制 historical replay
```

## 8. Development Order

建议按这个顺序做，避免一次性做太多：

1. Connection test only。
2. Print SPY / QQQ quote in terminal。
3. Add local buffer。
4. Add DuckDB insert。
5. Add Plotly static chart。
6. Add Dash auto refresh。
7. Add replay mode。
8. Run 30-60 minutes stability test。

## 9. Acceptance Criteria

Phase 1 完成标准：

1. OpenD 启动后，Python 能稳定连接。
2. 程序能每 1-5 秒获取 SPY / QQQ quote。
3. 闭市时可以用 historical data replay 模拟时间流逝。
4. 数据能持续写入 `underlying_quotes`。
5. Plotly panel 每 2 分钟刷新。
6. 能稳定显示 SPY / QQQ 实时或 replay 价格曲线。
7. 程序连续运行 30-60 分钟没有明显 crash 或 memory runaway。

## 10. Keep It Simple Notes

1. 第一版不要追求完美 realtime latency，先追求稳定。
2. 第一版不要同时接 Schwab，避免数据源复杂度上升。
3. 第一版 quote schema 固定下来，比 dashboard 好看更重要。
4. Replay mode 是为了开发效率，不需要完全模拟真实盘口。
5. 先保存 raw quote，再考虑指标计算。

