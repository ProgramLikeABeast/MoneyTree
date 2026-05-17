### 1. 项目目标

构建一个基于 Python 数据接口与 Plotly 图表的 0DTE 雷达原型系统，优先服务于 QQQ / SPY 的实时盘口监控、期权链追踪、VWAP / GWAP / 神掌类指标展示，以及后续交易信号评分系统。

第一版目标不是自动交易，而是完成：

1. 稳定接入实时标的价格。
2. 稳定拉取 0DTE 期权合约列表。
3. 对选中的期权合约进行分钟级 quote / snapshot 更新。
4. 每 2 分钟刷新一次图表面板，并保留历史指标轨迹。
5. 支持部分暂未自动接入的指标使用手动配置值。
6. 将实时数据、快照数据、指标数据落地到 DuckDB / Parquet，方便盘后复盘。

### 2. 核心技术栈

1. 后端与数据处理
   - Python
   - Moomoo SDK
   - Charles Schwab Developer API，作为第二数据源
   - DuckDB
   - Parquet
   - Pandas / Polars
   - APScheduler / asyncio

2. 图表与面板
   - Plotly
   - Dash 或 Streamlit，第一版建议优先 Dash
   - 未来可迁移到 Next.js + TypeScript 前端

3. 未来前端
   - Next.js
   - TypeScript
   - Plotly.js / Lightweight Charts
   - 本地部署或云端部署

### 3. 数据源优先级

1. 第一数据源：Moomoo API
   - Moomoo API 架构：

     ```text
     Python 程序
         ↓
     Moomoo SDK
         ↓
     OpenD 本地网关
         ↓
     Moomoo Server
         ↓
     市场行情 / 账户 / 交易数据
     ```

   - Moomoo 的 OpenD 是本地网关程序，SDK 连接 OpenD，而不是直接连接 moomoo 云端服务器。
   - 第一阶段只使用 Moomoo API 的行情能力，不接自动交易。

2. 第二数据源：Charles Schwab Developer API
   - 用途：
     1. 作为备用数据源。
     2. 作为某些字段的补充来源。
     3. 未来用于和 Moomoo 数据做一致性校验。
   - 第一版不要同时深度接入两个数据源，避免复杂度爆炸。先把 Moomoo 数据流跑通。

### 4. 关键概念澄清：Option Chain vs Quote vs Snapshot

1. Option Chain 是什么？
   - Option Chain 用于获取某个标的在某个到期日下的期权合约列表。
   - 它主要提供：
     - 合约 code
     - call / put 类型
     - strike
     - expiration
     - underlying
     - lot size
     - 合约基本属性
   - 在 Moomoo API 中，`get_option_chain` 主要返回期权链的静态信息。

2. Quote 是什么？
   - Quote 是某个具体证券或期权合约的实时行情。
   - 对于期权来说，quote / snapshot 可能包含：
     - bid
     - ask
     - last
     - volume
     - open interest
     - implied volatility
     - delta
     - gamma
     - theta
     - vega

3. Snapshot 是什么？
   - Snapshot 是某一刻对一批证券状态的快照。
   - 对于期权雷达来说，snapshot 更适合做分钟级批量刷新：

     ```text
     每分钟：
         对 ATM 附近 20-30 个 call 合约
         对 ATM 附近 20-30 个 put 合约
         拉一次 snapshot
         更新 bid / ask / mid / volume / Greeks
     ```

4. 三者关系

   ```text
   Option Chain:
       先找出有哪些合约可以看

   Quote / Snapshot:
       再对这些合约获取动态报价和 Greeks

   Subscription:
       对少数最重要的合约做实时推送
   ```

   也就是说：

   ```text
   期权链 ≠ 实时报价
   期权链 ≠ snapshot
   期权链 = 合约发现
   snapshot / quote = 动态行情
   ```

### 5. 系统数据流设计

系统数据流重新拆成五条主线。第一版以 real-time radar 为核心，historical 数据作为后台补全链路，不阻塞盘中雷达。

0. 数据流 0：休市期间的数据处理与先导开发流
   - 优先级：高
   - 目标：在非交易时段用历史 1m K 线模拟实时数据流，提前开发和测试 dashboard、数据湖写入、指标计算和 replay 逻辑。
   - 核心定位：
     - 这是 live radar 的 replay / simulation mode。
     - 不依赖实时行情。
     - 用历史分钟 K 线模拟盘中每一分钟的数据推进。
   - 标的：
     - US.QQQ
     - US.SPY
   - 输入数据：
     - 某一历史交易日的 1m K 线。
     - 可选：5m K 线。
     - 可选：盘前 / 盘后 K 线。
   - 数据字段：
     - symbol
     - replay_date
     - replay_timestamp
     - original_timestamp
     - interval
     - open
     - high
     - low
     - close
     - volume
     - session_type
     - replay_mode
     - source
   - replay_mode：
     - manual_step
     - auto_tick
     - fast_forward
   - 更新频率：
     - manual_step：手动点击一次，往前推进 1 分钟。
     - auto_tick：每 N 秒自动推进 1 根 1m bar。
     - fast_forward：快速播放完整交易日，用于测试图表和指标轨迹。
   - 处理逻辑：
     1. 选择一个历史交易日。
     2. 拉取 QQQ / SPY 当天 1m OHLCV。
     3. 写入 DuckDB / Parquet。
     4. 初始化 replay cursor。
     5. 每次 cursor 前进 1 分钟，模拟一次 live spot update。
     6. 更新 session_spot_high / session_spot_low。
     7. 驱动 Plotly dashboard 刷新。
     8. 触发指标计算，并写入 `radar_indicators`。
   - 用途：
     1. 在休市期间开发实时价格图。
     2. 测试 dashboard 是否能被 ticker 驱动。
     3. 测试手动推进、自动推进、暂停和重置。
     4. 测试 VWAP / session high-low / regime 等基础指标。
     5. 测试数据湖写入和 replay 数据读取。
   - 与正式实时流的关系：
     - 数据流 0 模拟数据流 A 的行为。
     - replay cursor 模拟 real-time clock。
     - dashboard 和指标引擎应复用 live mode 的接口。
   - 第一版完成标准：
     - 能导入某一天的 QQQ / SPY 1m K 线。
     - 能在 localhost dashboard 上按分钟推进价格图。
     - 支持手动 step 和 auto tick。
     - 支持暂停、继续、重置。
     - replay 数据和指标能写入 DuckDB / Parquet。

1. 数据流 A：实时标的价格流
   - 优先级：最高
   - 目标：秒级追踪 QQQ / SPY 的实时价格，作为整个雷达系统的底层价格基准。
   - 标的：
     - US.QQQ
     - US.SPY
   - 数据字段：
     - symbol
     - timestamp
     - bid
     - ask
     - mid
     - bid_size
     - ask_size
     - last
     - open
     - high
     - low
     - close
     - volume
     - turnover，可选
     - source
     - received_at
   - 更新频率：
     - 订阅制优先。
     - Data Push Frequency 初始设置为 1000ms。
     - 如果订阅不稳定，则使用 1-5 秒 polling fallback。
   - 用途：
     1. 绘制实时标的价格图。
     2. 生成秒级 spot price trace。
     3. 作为 VWAP / GWAP / regime 判断的底层价格输入。
     4. 作为筛选 ATM / OTM 期权合约的 spot reference。
     5. 实时更新 session_spot_high / session_spot_low。
   - 第一版完成标准：
     - 能连续显示 SPY / QQQ 秒级价格。
     - 能稳定写入 `underlying_quote_1s`。
     - 盘中运行 30 分钟以上不断流。

2. 数据流 B：期权链发现与动态合约池流
   - 优先级：高
   - 目标：获取 QQQ / SPY 当天到期的 0DTE option contracts，并维护一个动态的 radar universe。
   - 标的：
     - QQQ 0DTE options
     - SPY 0DTE options
   - 数据字段：
     - underlying
     - expiration
     - option_type: CALL / PUT
     - strike
     - contract_code
     - lot_size
     - option_standard_type
     - settlement_mode，可选
     - discovered_at
     - selected_for_radar
     - selected_reason
   - 更新频率：
     - 系统启动时获取一次。
     - 每 10-30 分钟刷新一次。
     - 当 spot price 移动超过 2-3 个 strike interval 时触发刷新。
     - 当 session_spot_high / session_spot_low 被突破时，扩展合约池。
   - 筛选逻辑：
     - 第一版使用动态区间：
       ```text
       lower_bound = floor_to_strike(session_spot_low) - 5 * strike_interval
       upper_bound = ceil_to_strike(session_spot_high) + 5 * strike_interval
       ```
     - 选择范围：
       - 当天到期。
       - strike 在 lower_bound 到 upper_bound 之间。
       - 同时包含 call 和 put。
   - 用途：
     1. 发现需要追踪的 option contract codes。
     2. 为后续 option quote snapshot 提供合约列表。
     3. 为 C/P Leg、GWAP、Put-Call Ratio 等指标提供 strike universe。
     4. 记录盘中 radar universe 如何随着 spot price 扩展。
   - 第一版完成标准：
     - 能稳定拿到 QQQ / SPY 当天到期期权合约 code。
     - 能根据 spot price 自动筛选 ATM 附近和动态扩展区间的 contracts。
     - 能写入 `option_contracts` 或 `option_universe_1m`。

3. 数据流 C：期权报价快照流
   - 优先级：最高
   - 目标：对数据流 B 中选中的 option contracts 进行分钟级 quote / Greeks / volume 快照。
   - 输入：
     - 来自数据流 B 的 selected contract_code 列表。
   - 数据字段：
     - contract_code
     - underlying
     - timestamp
     - option_type
     - strike
     - expiration
     - bid
     - ask
     - mid
     - last
     - volume
     - volume_change
     - open_interest
     - implied_volatility
     - delta
     - gamma
     - theta
     - vega
     - source
     - received_at
   - 第一版最低字段：
     - bid
     - ask
     - mid
     - last
     - volume
     - volume_change
     - delta
     - gamma
   - 更新频率：
     - 每 60 秒 snapshot 一次。
     - 如果 API 限制较紧，则每 120 秒 snapshot 一次。
   - 注意：
     - 不要对全部 option chain 做高频 snapshot。
     - 只对动态合约池中的 selected contracts 做 snapshot。
     - 这条数据流是实时雷达最核心的数据源。
   - 用途：
     1. 构建 option quote 1m 数据。
     2. 计算 C/P volume。
     3. 计算 Put-Call Ratio。
     4. 计算 C/P GWAP。
     5. 计算 Call-Put Premium Delta。
     6. 观察不同 strike 的 volume_change。
     7. 构建 option flow heatmap。
   - 第一版完成标准：
     - 能每分钟保存 selected contracts 的 bid / ask / mid / volume / gamma。
     - 能看到 ATM 附近 call / put 的 volume、gamma、delta 随时间变化。
     - 能写入 `option_quote_1m`。

4. 数据流 D：实时指标计算与雷达状态流
   - 优先级：高
   - 目标：基于实时标的价格和期权报价快照，计算雷达指标，并输出 dashboard 可直接读取的实时状态。
   - 输入：
     - 数据流 A：实时标的价格。
     - 数据流 C：期权报价快照。
     - 手动 fallback 配置，可选。
   - 输出：
     - VWAP
     - C/P/O VWAP
     - C-GWAP
     - P-GWAP
     - Total GWAP
     - C/P Leg
     - Call-Put Premium Delta
     - Put-Call Ratio
     - Volume Change
     - Radar Signal Score
   - 数据字段：
     - symbol
     - timestamp
     - indicator_name
     - indicator_value
     - source_mode: calculated / manual / fallback
     - direction
     - score
     - weight
     - source
   - 更新频率：
     - 每 120 秒计算一次。
     - Dashboard 每 120 秒刷新一次。
     - 关键状态可以保存在 memory state 中，避免 dashboard 频繁扫大文件。
   - 用途：
     1. 给 dashboard 提供连续指标轨迹。
     2. 给入场信号提供评分基础。
     3. 给盘后复盘提供指标快照。
     4. 将多个信号聚合成 bullish / bearish / neutral 状态。
   - 第一版完成标准：
     - Dashboard 能显示连续的 VWAP / GWAP / PCR / Premium Delta。
     - 每次刷新保留历史轨迹。
     - 能写入 `radar_indicators`。

5. 数据流 E：后台历史数据与 Data Lake 补全流
   - 优先级：中
   - 目标：盘后或后台慢慢补充 historical 数据，构建 research / backtest / ML 所需的数据湖，不阻塞实时雷达。
   - 标的：
     - QQQ
     - SPY
     - 后续可扩展到更多 underlyings。
   - 时间区间：
     1. 前一交易日 regular session。
     2. 前一交易日 after-hours。
     3. 今日 pre-market。
     4. 今日 regular session。
     5. 历史任意指定日期。
   - K 线粒度：
     - 第一版：1m、5m。
     - 第二版：30m、daily。
   - 数据字段：
     - symbol
     - timestamp
     - interval
     - open
     - high
     - low
     - close
     - volume
     - session_type
     - source
   - 更新频率：
     - 不参与盘中实时主链路。
     - 每天盘后 cron job 执行。
     - 可按需补过去某一天或过去一段时间的数据。
   - 用途：
     1. 补全 underlying historical bars。
     2. 校验盘中 real-time 数据是否缺失。
     3. 生成 daily replay dataset。
     4. 重新计算 VWAP / GWAP / PCR / Premium Delta。
     5. 为 research、backtest、ML 特征工程提供数据。
   - 第一版完成标准：
     - 每天盘后能自动拉取 SPY / QQQ 1m / 5m K 线。
     - 能保存到 DuckDB / Parquet。
     - 不影响实时 dashboard 和 live signal。

### 6. 图表面板设计

1. 刷新机制
   - 面板每 2 分钟刷新一次。
   - 显示刷新倒计时：

     ```text
     Next refresh in: 01:37
     ```

   - 每次刷新不覆盖历史 trace，而是追加新数据点。

2. 图表 1：标的实时价格图
   - 显示：
     - QQQ / SPY spot price
     - 1m candle
     - bid / ask，可选
     - VWAP
     - pre-market high / low
     - previous day high / low / close

3. 图表 2：C/P/O VWAP 图
   - 显示：
     - C-VWAP
     - P-VWAP
     - O-VWAP
     - C-VWAP high / low
     - P-VWAP high / low
     - O-VWAP high / low
   - 如果部分数据暂未自动实现，则使用手动配置值。

4. 图表 3：GWAP 图
   - 显示：
     - C-GWAP
     - P-GWAP
     - Total GWAP
     - spot price overlay，可选

5. 图表 4：Call-Put Premium Delta
   - 显示：
     - call premium total
     - put premium total
     - call-put premium delta
     - delta change over time

6. 图表 5：Put-Call Ratio
   - 显示：
     - call volume
     - put volume
     - put-call volume ratio
     - ratio change over time

7. 图表 6：Option Strike Heatmap
   - 显示：
     - strike
     - call volume
     - put volume
     - call gamma
     - put gamma
     - volume change
     - gamma-weighted volume

8. 图表 7：Radar Signal Panel
   - 显示多个入场信号：
     - trend confirmation
     - VWAP alignment
     - C/P Leg signal
     - C/P GWAP signal
     - premium delta signal
     - put-call ratio signal
     - volume expansion signal
   - 每个信号显示：
     - signal_name
     - current_value
     - direction
     - weight
     - score
     - status

### 7. 第一版需要实现的指标

1. Spot Price
   - 来源：
     - 实时标的价格流。
   - 用途：
     - 所有指标的底层价格基准。

2. VWAP
   - 计算：

     ```text
     VWAP = sum(price * volume) / sum(volume)
     ```

   - 第一版 price 可以使用 typical price：

     ```text
     typical_price = (high + low + close) / 3
     ```

3. C/P/O VWAP
   - 定义：
     - C-VWAP = Call-side VWAP。
     - P-VWAP = Put-side VWAP。
     - O-VWAP = Overall option VWAP。
   - 第一版如果神掌书中具体公式尚未完全确认，则做两套设计：
     1. manual_mode
     2. calculated_mode
   - manual_mode 示例：

     ```yaml
     manual_indicators:
       c_vwap: 123.45
       p_vwap: 122.80
       o_vwap: 123.10
       c_vwap_high: 124.00
       c_vwap_low: 122.50
       p_vwap_high: 123.20
       p_vwap_low: 121.90
     ```

   - calculated_mode：
     - 后续由期权报价流自动计算。

4. GWAP
   - 第一版定义：

     ```text
     GWAP = sum(price * gamma * volume) / sum(gamma * volume)
     ```

   - Call / Put 分开计算：
     - C-GWAP = call side gamma-weighted average price。
     - P-GWAP = put side gamma-weighted average price。
   - 注意：
     - 如果 gamma 缺失，则该合约不参与 GWAP 计算，或者使用 fallback gamma = 0。

5. C/P Leg
   - 第一版先抽象成方向性指标：

     ```text
     C/P Leg = call side pressure vs put side pressure
     ```

   - 初版可用：

     ```text
     call_pressure = sum(call_mid * call_volume)
     put_pressure = sum(put_mid * put_volume)

     cp_leg = call_pressure - put_pressure
     ```

   - 后续根据神掌书中的具体定义修正。

6. Call-Put Premium Delta
   - 第一版定义：

     ```text
     call_premium = sum(call_mid * call_volume * 100)
     put_premium = sum(put_mid * put_volume * 100)

     call_put_premium_delta = call_premium - put_premium
     ```

   - 可进一步标准化：

     ```text
     normalized_delta = (call_premium - put_premium) / (call_premium + put_premium)
     ```

7. Put-Call Ratio
   - 第一版使用 volume-based PCR：

     ```text
     PCR = put_volume / call_volume
     ```

   - 后续增加：
     - premium_pcr = put_premium / call_premium
     - oi_pcr = put_open_interest / call_open_interest

8. Volume and Volume Changes
   - 每次 option snapshot 后计算：

     ```text
     volume_change = current_volume - previous_volume
     volume_change_rate = volume_change / previous_volume
     ```

   - 用途：
     1. 判断某些 strike 是否突然放量。
     2. 观察 call / put 哪边突然增强。
     3. 构建 strike-level heatmap。

### 8. 数据存储设计

1. 实时标的价格表
   - table: `underlying_quotes`
   - columns:
     - symbol
     - timestamp
     - bid
     - ask
     - last
     - open
     - high
     - low
     - close
     - volume
     - source
     - received_at

2. 标的 K 线表
   - table: `underlying_bars`
   - columns:
     - symbol
     - timestamp
     - interval
     - open
     - high
     - low
     - close
     - volume
     - session_type
     - source

3. 期权合约表
   - table: `option_contracts`
   - columns:
     - underlying
     - contract_code
     - expiration
     - strike
     - option_type
     - lot_size
     - source
     - discovered_at

4. 期权快照表
   - table: `option_snapshots`
   - columns:
     - contract_code
     - underlying
     - timestamp
     - expiration
     - strike
     - option_type
     - bid
     - ask
     - mid
     - last
     - volume
     - volume_change
     - open_interest
     - implied_volatility
     - delta
     - gamma
     - theta
     - vega
     - source
     - received_at

5. 指标表
   - table: `radar_indicators`
   - columns:
     - symbol
     - timestamp
     - indicator_name
     - indicator_value
     - source_mode
     - source
   - source_mode:
     - calculated
     - manual
     - fallback

### 9. 系统模块划分

1. 项目目录结构

   ```text
   /
     data/
       providers/
         base.py
         moomoo_provider.py
         schwab_provider.py

       models/
         underlying_quote.py
         underlying_bar.py
         option_contract.py
         option_snapshot.py

       services/
         market_data_service.py
         option_chain_service.py
         option_snapshot_service.py
         historical_bar_service.py

       storage/
         duckdb_store.py
         parquet_store.py

     indicators/
       vwap.py
       gwap.py
       cp_leg.py
       premium_delta.py
       put_call_ratio.py
       volume_change.py

     dashboard/
       app.py
       charts/
         price_chart.py
         vwap_chart.py
         gwap_chart.py
         premium_delta_chart.py
         pcr_chart.py
         option_heatmap.py
         signal_panel.py

     config/
       symbols.yaml
       manual_indicators.yaml
       data_source.yaml

     scripts/
       run_realtime_radar.py
       fetch_previous_day_bars.py
       refresh_option_chain.py

     tests/
       test_option_chain_filter.py
       test_gwap.py
       test_premium_delta.py
       test_storage.py
   ```

### 10. 系统启动流程

1. Step 1：启动 OpenD
   - 确保：
     - OpenD 已启动。
     - moomoo 账号已登录。
     - API port 可连接。
     - 行情权限可用。

2. Step 2：启动 Python Radar

   ```text
   python scripts/run_realtime_radar.py
   ```

3. Step 3：初始化历史数据
   - 系统启动时自动拉取：
     - 前一交易日 1m / 5m K线。
     - 前一交易日 after-hours。
     - 今日 pre-market。

4. Step 4：初始化实时标的订阅
   - 订阅：
     - US.QQQ
     - US.SPY

5. Step 5：初始化期权链
   - 获取：
     - QQQ 今日到期期权链。
     - SPY 今日到期期权链。
   - 筛选：
     - ATM 附近 20-30 个 call。
     - ATM 附近 20-30 个 put。

6. Step 6：启动期权快照任务
   - 每 60 秒：
     - 对筛选后的期权合约列表请求 snapshot。
     - 保存到 option_snapshots。
     - 计算 volume_change。
     - 计算 Greeks-based 指标。

7. Step 7：启动指标计算任务
   - 每 120 秒：
     - 计算 VWAP。
     - 计算 C/P/O VWAP。
     - 计算 C/P GWAP。
     - 计算 C/P Leg。
     - 计算 Call-Put Premium Delta。
     - 计算 Put-Call Ratio。
     - 计算 volume changes。
     - 更新 radar_indicators。

8. Step 8：刷新 Dashboard
   - 每 120 秒刷新图表。
   - 显示倒计时：

     ```text
     Next refresh in: 02:00
     ```

### 11. 实施优先级

1. Phase 1：最小可运行数据闭环
   - 目标：
     ```text
     Moomoo OpenD → Python SDK → SPY/QQQ 实时价格 → Plotly 图表
     ```
   - 实现：
     1. 启动 OpenD。
     2. Python 连接 OpenD。
     3. 获取 SPY / QQQ 实时 quote。
     4. 每 1-5 秒更新本地数据。
     5. 每 2 分钟刷新 Plotly 面板。
     6. 保存 underlying_quotes。
   - 完成标准：
     - 能稳定显示 SPY / QQQ 实时价格曲线。

2. Phase 2：期权链发现与筛选
   - 目标：
     - 获取 QQQ / SPY 0DTE option chain。
     - 筛选 ATM 附近合约。
     - 保存 option_contracts。
   - 实现：
     1. 获取今日到期日。
     2. 获取 option chain。
     3. 根据 spot price 选择 strike。
     4. 分 call / put 保存合约列表。
   - 完成标准：
     - 能稳定拿到 QQQ / SPY 当天到期期权合约 code。

3. Phase 3：期权快照与 Greeks
   - 目标：
     - 每分钟获取重点合约 bid / ask / volume / Greeks。
   - 实现：
     1. 对筛选后的期权 code 请求 snapshot。
     2. 计算 mid。
     3. 计算 volume_change。
     4. 保存 option_snapshots。
   - 完成标准：
     - 能看到 ATM 附近 call / put 的 volume、gamma、delta 随时间变化。

4. Phase 4：核心指标计算
   - 目标：
     - VWAP / GWAP / C-P Premium Delta / PCR。
   - 实现：
     1. VWAP。
     2. C/P GWAP。
     3. Call-Put Premium Delta。
     4. Put-Call Ratio。
     5. Volume change。
   - 完成标准：
     - 图表上能看到每 2 分钟刷新的指标轨迹。

5. Phase 5：手动指标 fallback
   - 目标：
     - 神掌书中暂未实现的指标，可以先手动录入。
   - 实现：
     1. manual_indicators.yaml。
     2. dashboard 读取 manual 值。
     3. 图表标记该数据为 manual。
   - 完成标准：
     - 未自动化的 C/P/O VWAP high / low 等指标也能先展示在面板中。

6. Phase 6：Radar Signal Scoring
   - 目标：
     - 多个信号加权评分。
   - 实现：
     1. 每个信号一个 score。
     2. 每个信号一个 weight。
     3. 输出 total_score。
     4. 显示入场方向倾向。
   - 示例：

     ```text
     total_score = sum(signal_score * weight)
     ```

   - 完成标准：
     - dashboard 能显示 bullish / bearish / neutral 雷达评分。

### 12. 关于“买入 / 卖出 / 平仓分类”的处理

1. 第一版不要强行判断每笔期权成交是买入、卖出、开仓、平仓。

2. 原因：
   1. 普通 quote / snapshot 通常不能直接告诉你成交是 buyer-initiated 还是 seller-initiated。
   2. open / close classification 通常需要更细的 trade-level 数据、OI 变化、成交价相对 bid / ask 的位置，以及交易所级别数据。
   3. 这个模块容易引入大量误判。

3. 第一版只做：
   - volume
   - volume_change
   - premium_change
   - bid / ask / mid
   - strike-level concentration
   - call vs put imbalance

4. 第二版再考虑推断：
   - buyer_initiated_estimate：
     - 如果 trade_price 接近 ask，估计主动买入。
     - 如果 trade_price 接近 bid，估计主动卖出。
   - open_close_estimate：
     - 使用 volume change + OI 次日变化做弱推断。

5. 这类分类只能叫 estimate，不能当成真实标签。

### 13. v0.1 不做的事情

为了控制复杂度，第一版暂时不做：

1. 自动下单。
2. tick-level replay。
3. 全市场扫描。
4. 复杂订单簿。
5. ML 模型。
6. 多数据源实时融合。
7. 精确判断买入 / 卖出 / 开仓 / 平仓。
8. 秒级全期权链 Greeks 更新。
9. 云端部署。
10. 移动端提醒。

### 14. v0.1 成功标准

如果第一版完成，系统应该做到：

1. 启动 OpenD。
2. 启动 Python radar。
3. 自动显示 QQQ / SPY 实时价格。
4. 自动获取 QQQ / SPY 0DTE option chain。
5. 自动筛选 ATM 附近 call / put 合约。
6. 每分钟获取这些合约的 quote / snapshot。
7. 每两分钟刷新 Plotly dashboard。
8. 图表中保留过去指标轨迹。
9. 数据落地到 DuckDB / Parquet。
10. 支持手动配置未实现的神掌指标。

### 15. 最终架构图

```text
[Moomoo Server]
      ↑↓
[OpenD Gateway]
      ↑↓
[Moomoo SDK]
      ↑↓
[MoomooProvider]
      ↑↓
[MarketDataService]
      ├── Underlying Realtime Stream
      ├── Option Chain Discovery
      ├── Option Snapshot Stream
      └── Historical Bar Loader
      ↑↓
[DuckDB / Parquet]
      ↑↓
[Indicator Engine]
      ├── VWAP
      ├── C/P/O VWAP
      ├── GWAP
      ├── C/P Leg
      ├── Premium Delta
      ├── Put-Call Ratio
      └── Volume Change
      ↑↓
[Plotly / Dash Dashboard]
      ↑↓
[Future Next.js Frontend]
```

### 16. 核心结论

1. 期权链是“找合约”，quote / snapshot 是“看这些合约现在多少钱、多少量、Greeks 是多少”。

2. 所以系统数据流不要写成：

   ```text
   每分钟快照一次期权链
   ```

3. 而应该写成：

   ```text
   启动 / 定期刷新：获取 option chain，发现合约。
   每分钟：对筛选后的 option contract codes 拉 quote / snapshot。
   ```

4. 这样架构更清楚，也更接近 Moomoo API 的实际使用方式。
