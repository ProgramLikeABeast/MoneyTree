# 0DTE Radar Prototype File Guide

This document explains the current files under `0dte-radar-prototype/`.

The folder is now a small Phase 1 prototype for a minimal local data loop:

```text
Moomoo OpenD -> Python SDK -> SPY / QQQ quotes -> DuckDB -> Plotly
```

Current work is focused on connecting to Moomoo OpenD, collecting `US.SPY` and `US.QQQ` quotes, replaying historical bars when the market is closed, saving `underlying_quotes`, and displaying a simple Plotly panel.

---

## Current Tree

```text
0dte-radar-prototype/
  .env.example
  README.md
  pyproject.toml
  docs/
    0dte-radar-prototype.md
    phase-1-minimal-data-loop.md
  src/
    __init__.py
    config.py
```

The previous FlowLab-oriented files are no longer present in the current project tree. That includes:

```text
notebooks/
src/data/
src/indicators/
src/egg-info/
```

Those older files documented Massive API ingestion, Parquet lake helpers, DuckDB catalog views, data quality notebooks, and VWAP reconstruction. The current prototype has been reset around Moomoo quote collection and does not yet contain those implementation modules.

---

## Top-Level Files

### `0dte-radar-prototype/README.md`

Short project summary for the current prototype.

It states that Phase 1 should stay focused on:

- Connecting to Moomoo OpenD through the Python SDK.
- Collecting `US.SPY` and `US.QQQ` quotes.
- Using historical bar replay when the market is closed.
- Saving data to `underlying_quotes`.
- Displaying a simple Plotly panel.

The README intentionally stays brief. Detailed planning lives in `docs/`.

### `0dte-radar-prototype/pyproject.toml`

Python packaging and dependency configuration.

Current responsibilities:

- Defines the distribution name as `odte-radar-prototype`.
- Sets version `0.1.0`.
- Requires Python `>=3.10`.
- Declares runtime dependencies:
  - `dash`
  - `duckdb`
  - `moomoo`
  - `pandas`
  - `plotly`
  - `python-dotenv`
- Tells setuptools to find packages under `src`.

Current caveat:

- The package include rule is `include = ["data*"]`, but the current `src/` tree only contains `__init__.py` and `config.py`.
- If a package named `data` is planned, the future `src/data/` package should be added.
- If the intended import package is the prototype itself, the packaging layout should be revisited before adding runnable modules.

Editable install command:

```bash
cd 0dte-radar-prototype
.venv/bin/python -m pip install -e .
```

### `0dte-radar-prototype/.env.example`

Template for local runtime configuration.

Current variables:

- `MOOMOO_HOST`: OpenD host, defaulting to `127.0.0.1`.
- `MOOMOO_PORT`: OpenD API port, defaulting to `11111`.
- `SYMBOLS`: comma-separated quote symbols, defaulting to `US.SPY,US.QQQ`.
- `QUOTE_INTERVAL_SECONDS`: quote polling interval, defaulting to `2`.
- `PLOT_REFRESH_SECONDS`: dashboard refresh interval, defaulting to `120`.
- `DATA_MODE`: runtime mode, currently intended to support values such as `auto`, `realtime`, and `replay`.
- `ODTE_RADAR_DATA_DIR`: local data directory, defaulting to `data`.

Copy this file to `.env` before running local scripts:

```bash
cd 0dte-radar-prototype
cp .env.example .env
```

The real `.env` should not be committed.

---

## Source Files

### `0dte-radar-prototype/src/__init__.py`

Current root initializer for the source tree.

It defines:

```python
__version__ = "0.1.0"
```

Current caveat:

- In a conventional `src` layout, `src/` is not itself the import package. Usually a real package directory lives under `src/`, such as `src/odte_radar_prototype/`.
- This file currently acts as a placeholder while the package layout is still minimal.

### `0dte-radar-prototype/src/config.py`

Runtime configuration module for the Phase 1 Moomoo quote loop.

Main responsibilities:

- Loads `.env` through `python-dotenv`.
- Resolves `PROJECT_ROOT`.
- Reads local data storage settings.
- Reads Moomoo OpenD connection settings.
- Reads quote/dashboard timing settings.
- Parses the configured symbol list.
- Defines a frozen `Settings` dataclass for shared runtime configuration.

Important settings:

- `project_root`: resolved project path.
- `data_dir`: root local data directory.
- `moomoo_host`: OpenD host.
- `moomoo_port`: OpenD port.
- `symbols`: tuple of configured symbols.
- `quote_interval_seconds`: quote polling interval.
- `plot_refresh_seconds`: Plotly/Dash refresh interval.
- `data_mode`: selected runtime mode.
- `duckdb_path`: derived path at `data/duckdb/odte_radar.duckdb`.

Path behavior:

- `PROJECT_ROOT = Path(__file__).resolve().parents[1]` resolves to `0dte-radar-prototype/`.
- `.env` is loaded from `0dte-radar-prototype/.env`.
- A relative `ODTE_RADAR_DATA_DIR=data` resolves to `0dte-radar-prototype/data`.

Important symbols:

- `PROJECT_ROOT`
- `Settings`
- `Settings.duckdb_path`
- `get_settings()`

---

## Documentation Files

### `0dte-radar-prototype/docs/phase-1-minimal-data-loop.md`

Phase 1 implementation plan for the minimal working data loop.

It defines the near-term scope:

- Start and connect Moomoo OpenD.
- Use the Moomoo Python SDK to collect `US.SPY` and `US.QQQ` quotes.
- Maintain a local quote buffer.
- Support market-closed historical replay.
- Persist quote records to DuckDB table `underlying_quotes`.
- Display SPY/QQQ prices in a Plotly or Dash panel.

It also defines the proposed `underlying_quotes` schema:

```text
symbol
timestamp
bid
ask
last
open
high
low
close
volume
source
mode
received_at
```

The file includes a suggested future layout:

```text
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

Those modules are planned but not implemented in the current tree.

### `0dte-radar-prototype/docs/0dte-radar-prototype.md`

Broader architecture and product-design document for the 0DTE radar prototype.

It describes the longer-term system beyond the minimal Phase 1 loop:

- Moomoo as the first market data source.
- Charles Schwab as a future secondary data source.
- Underlying quote flow.
- Option chain discovery.
- Option quote/snapshot flow.
- Historical bar loading.
- VWAP, GWAP, C/P Leg, premium delta, put-call ratio, and volume-change indicators.
- DuckDB/Parquet storage plans.
- Plotly/Dash dashboard plans.
- Later radar signal scoring.

This document is aspirational architecture, not a list of implemented files. The current codebase only implements the initial configuration layer.

---

## Local Data And Generated Artifacts

### `0dte-radar-prototype/data/`

Local data is planned but not currently present in the tracked tree.

When Phase 1 storage is implemented, `config.py` expects DuckDB to live at:

```text
0dte-radar-prototype/data/duckdb/odte_radar.duckdb
```

This database should be treated as local generated data and usually kept out of git.

### Removed Generated Metadata

The previous `src/egg-info/` generated packaging metadata is no longer present.

That is a good cleanup: packaging metadata should be regenerated by the packaging toolchain, not maintained by hand.

---

## How The Current Files Fit Together

```text
.env / .env.example
  -> src/config.py
  -> future quote collector
  -> future DuckDB storage at data/duckdb/odte_radar.duckdb
  -> future Plotly/Dash panel
```

In short:

- `.env.example` documents local configuration.
- `config.py` resolves that configuration into a `Settings` object.
- `README.md` summarizes the current Phase 1 target.
- `phase-1-minimal-data-loop.md` describes the immediate implementation path.
- `0dte-radar-prototype.md` captures the broader roadmap.

---

## Follow-Up To Consider

The next implementation step is to decide the package layout before adding the quote collector modules.

Recommended layout for a packaged Python project:

```text
0dte-radar-prototype/src/odte_radar_prototype/
  __init__.py
  config.py
  data/
  dashboard/
```

If this direction is chosen, update `pyproject.toml` to include:

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["odte_radar_prototype*"]
```

Then future imports can consistently use:

```python
from odte_radar_prototype.config import get_settings
```
