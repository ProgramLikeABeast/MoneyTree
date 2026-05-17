# Phase 1：休市 Replay / Simulation 最小数据闭环

## 1. Goal

本阶段目标调整为：先跑通一个不依赖盘中实时行情的 replay / simulation data loop。

```text
Historical 1m K-line -> Replay Cursor -> Local State / Storage -> Localhost Dashboard
```

Phase 1 的核心不是先做完整 live radar，而是先验证：

> Python 能稳定从 Moomoo OpenD 获取某个历史交易日的 SPY / QQQ 1m K 线，并用 replay cursor 在 localhost dashboard 上模拟盘中每一分钟的数据推进。

这对应总设计文档第五节里的“数据流 0：休市期间的数据处理与先导开发流”。它是 live radar 的 replay / simulation mode，用来提前开发 dashboard、数据湖写入、基础指标计算和 replay 控制逻辑。

---

## 2. Scope

### In Scope

1. 启动并连接 Moomoo OpenD。
2. Python SDK 获取 `US.SPY` / `US.QQQ` 某一历史交易日的 1m K 线。
3. 保存 historical 1m OHLCV 到本地 DuckDB / Parquet。
4. 初始化 replay cursor。
5. 支持手动 step：点击一次推进 1 分钟。
6. 支持 auto tick：每 N 秒自动推进 1 根 1m bar。
7. 支持暂停、继续、重置。
8. 输出统一的 replay spot update，供 dashboard 和后续指标模块使用。
9. 在 localhost dashboard 上显示 SPY / QQQ replay price line。
10. 更新基础 session state，例如 `session_spot_high` / `session_spot_low`。

### Out of Scope

1. 盘中 live subscription 主链路。
2. 期权链 discovery。
3. 期权 quote / snapshot。
4. Greeks。
5. C/P/O VWAP、GWAP、Premium Delta、PCR 等完整雷达指标。
6. Radar signal scoring。
7. 自动下单。
8. Cloud deployment。

---

## 3. Simple Architecture

休市 replay 模式：

```text
[Moomoo OpenD]
      ↓
[Moomoo Python SDK]
      ↓
[Historical 1m K-line Request]
      ↓
[DuckDB / Parquet Historical Store]
      ↓
[Replay Cursor]
      ↓
[In-memory Replay State]
      ↓
[Localhost Dashboard]
```

实时模式后续会复用同一套 dashboard / state / storage 接口：

```text
[Realtime Quote Stream]
      ↓
[Same State Interface]
      ↓
[Same Dashboard]
```

关键原则：replay mode 和 future live mode 尽量输出同一种 spot update schema。这样 dashboard 和指标引擎不需要关心数据来自 historical replay 还是 real-time quote。

---

## 4. Data Schema

Phase 1 先围绕两类数据：historical bars 和 replay updates。

### Historical 1m Bars

建议表名：

```text
underlying_bars_1m
```

建议字段：

```text
symbol          text        # US.SPY / US.QQQ
timestamp       timestamp   # original market timestamp, US Eastern for US stocks
interval        text        # 1m
open            double
high            double
low             double
close           double
volume          bigint
session_type    text        # REGULAR / PRE_MARKET / AFTER_HOURS
source          text        # moomoo_history_kline
inserted_at     timestamp   # local insert time
```

### Replay Spot Updates

建议表名：

```text
underlying_replay_updates
```

建议字段：

```text
symbol              text
replay_date         date
replay_timestamp    timestamp   # simulated current replay time
original_timestamp  timestamp   # original historical bar timestamp
interval            text        # 1m
open                double
high                double
low                 double
close               double
volume              bigint
session_type        text
replay_mode         text        # manual_step / auto_tick / fast_forward
source              text        # moomoo_history_replay
emitted_at          timestamp   # local emit time
```

Dashboard 第一版可以直接使用 `close` 作为 replay spot price。后续如果要让 replay output 更接近 quote schema，可以再补 `last = close`、`bid = null`、`ask = null`。

---

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
4. 写一个最小 connection test 或使用 historical K-line request 验证连接。

完成标准：

- Python 能成功 connect OpenD。
- 失败时能打印清楚错误，比如 OpenD 未启动、端口不对、权限不足。

### Step 2：Historical 1m K-line Loader

目标：获取 SPY / QQQ 某一历史交易日的 regular-session 1m K 线。

要做：

1. 使用 Moomoo Python SDK 创建 quote context。
2. 调用 `request_history_kline(...)`。
3. 参数优先保持简单：

   ```text
   code = US.SPY / US.QQQ
   start = selected_trade_date
   end = selected_trade_date
   ktype = KLType.K_1M
   session = Session.RTH
   extended_time = False
   max_count = 1000
   ```

4. 支持 paging 的 `page_req_key`，避免未来扩展时被 max count 限制。
5. 保留 09:30-16:00 regular session 数据。

完成标准：

- 能拿到 SPY / QQQ 某一天的 1m OHLCV。
- 完整 regular session 通常约 390 rows。
- 半日交易、停牌或数据缺失时允许少于 390 rows，但需要能被检查出来。

### Step 3：Local Historical Store

目标：把 historical 1m bars 落地，后续 replay 不需要每次重新请求 Moomoo。

要做：

1. 使用 DuckDB 创建 `underlying_bars_1m`。
2. 可选同步写 Parquet，作为 data lake 文件层。
3. 用 `symbol + timestamp + interval` 作为去重逻辑。
4. 保存 source 和 insert time。

完成标准：

- DuckDB 中能查到 SPY / QQQ historical 1m bars。
- 停止程序后数据仍然存在。
- 重复导入同一天数据不会产生明显重复行。

### Step 4：Replay Cursor

目标：用 historical bars 模拟盘中时间推进。

要做：

1. 选择 replay date。
2. 读取 SPY / QQQ 当天 1m bars。
3. 初始化 cursor 到第一根 regular-session bar。
4. 每次 cursor 前进 1 分钟，输出当前 bar 对应的 replay spot update。
5. 支持三种模式：

   ```text
   manual_step    手动点击一次，推进 1 分钟
   auto_tick      每 N 秒自动推进 1 根 1m bar
   fast_forward   快速播放完整交易日，用于测试图表和指标轨迹
   ```

完成标准：

- 可以手动 step。
- 可以 auto tick。
- 可以暂停、继续、重置。
- cursor 到交易日末尾时能明确停止或循环重置。

### Step 5：Replay State And Basic Metrics

目标：维护 dashboard 需要的最小状态。

要做：

1. 保存当前 replay timestamp。
2. 保存 SPY / QQQ latest close。
3. 更新 `session_spot_high`。
4. 更新 `session_spot_low`。
5. 保存当前 replay mode。
6. 可选：把 replay update 写入 `underlying_replay_updates`。

完成标准：

- Dashboard 可以直接读取 latest state。
- 图表可以追加历史 trace，而不是每次覆盖。
- session high / low 能随着 replay 推进变化。

### Step 6：Localhost Dashboard

目标：展示 SPY / QQQ replay price line。

要做：

1. 前端或本地 dashboard 调用 Python 数据接口。
2. 显示两条 line：
   - SPY replay price
   - QQQ replay price
3. 页面显示：
   - replay mode
   - replay timestamp
   - latest SPY / QQQ close
   - session high / low
   - data source
4. 提供 replay 控制：
   - step
   - play
   - pause
   - reset

完成标准：

- 能在 localhost dashboard 上按分钟推进价格图。
- 手动 step 和 auto tick 都能驱动图表变化。
- dashboard 不需要知道后续 live data 的内部细节。

---

## 6. Suggested File Layout

可以保持简单，不需要过早拆太细。

```text
0dte-radar-prototype/
  src/
    config.py
    data/
      request_1m_kline.py
      historical_store.py
      replay_cursor.py
      replay_state.py
    dashboard/
      price_panel.py
  data/
    duckdb/
      odte_radar.duckdb
    parquet/
      underlying_bars_1m/
```

每个文件职责：

```text
config.py              读取 OpenD host / port / symbols / mode
request_1m_kline.py    从 Moomoo 获取 historical 1m K 线
historical_store.py    DuckDB / Parquet historical bars 写入和查询
replay_cursor.py       replay cursor、step、play、pause、reset
replay_state.py        latest replay state、session high / low
price_panel.py         localhost dashboard / Plotly price chart
```

---

## 7. Config Draft

可以先用简单 `.env`：

```text
MOOMOO_HOST=127.0.0.1
MOOMOO_PORT=11111
SYMBOLS=US.SPY,US.QQQ
DATA_MODE=replay
```

`DATA_MODE` 建议支持：

```text
replay     使用 historical 1m bars 模拟盘中推进
realtime   后续强制使用 live quote stream
auto       后续 market open 用 realtime，closed 用 replay
```

Phase 1 可以先默认使用 `replay`，等 live quote stream 稳定后再把 `auto` 作为默认模式。

---

## 8. Development Order

建议按这个顺序做，避免一次性做太多：

1. OpenD connection test。
2. 拉取单个 symbol / 单个日期的 1m K 线。
3. 扩展到 SPY / QQQ。
4. 写入 DuckDB。
5. 读取 DuckDB 并初始化 replay cursor。
6. 实现 manual step。
7. 实现 localhost price chart。
8. 实现 auto tick / pause / reset。
9. 增加 session high / low。
10. 再考虑 Parquet 同步和 fast forward。

---

## 9. Acceptance Criteria

Phase 1 完成标准：

1. OpenD 启动后，Python 能稳定连接。
2. 能导入某一天的 SPY / QQQ regular-session 1m K 线。
3. historical bars 能保存到 DuckDB，后续可重复读取。
4. replay cursor 能按分钟推进。
5. localhost dashboard 能显示 SPY / QQQ replay price line。
6. 支持手动 step、auto tick、暂停、继续、重置。
7. replay state 能维护 latest price、replay timestamp、session high / low。
8. replay 数据结构能为后续 live mode 复用，避免 dashboard 重写。

---

## 10. Keep It Simple Notes

1. 第一版先做 replay，不要急着接完整 live subscription。
2. 第一版先使用 1m regular-session K 线，不要一开始处理盘前 / 盘后 / overnight。
3. 第一版只做 SPY / QQQ，不要扩展到全市场。
4. 第一版 dashboard 先显示 price line 和基础状态，不要提前做复杂指标。
5. replay mode 是为了开发效率，不需要完全模拟真实盘口。
6. 先把数据接口做成 frontend 可以直接调用的函数，不需要 command-line wrapper。
