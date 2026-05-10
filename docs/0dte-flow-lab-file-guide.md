# 0DTE FlowLab File Guide

This document explains the current files under `0dte-flow-lab/` after the latest refactor.

`0dte-flow-lab/` is the strategy-specific research lab inside the broader `MoneyTree` repository. The files in this folder are focused on the first 0DTE FlowLab milestone: local SPY/QQQ 1-minute data ingestion, DuckDB + Parquet storage, data checks, and regular VWAP reconstruction.

---

## Current Refactor Note

The current source tree has been flattened to:

```text
0dte-flow-lab/src/
  __init__.py
  config.py
  data/
  indicators/
```

However, some current imports, notebooks, and generated metadata still reference `odte_flow_lab`, for example:

```python
from odte_flow_lab.config import get_settings
```

and `pyproject.toml` still has:

```toml
include = ["odte_flow_lab*"]
```

So this guide documents the files as they exist now, but the packaging/import path should be reviewed in a follow-up. Either restore a real `src/odte_flow_lab/` package directory, or update imports and packaging to match the flattened `src/` layout.

---

## Top-Level Files

### `0dte-flow-lab/README.md`

Short summary for the lab.

It states that this folder contains local research tooling for:

- Ingesting SPY/QQQ intraday data.
- Storing data in a DuckDB + Parquet lake.
- Rebuilding intraday indicators.

This file is intentionally short. More detailed explanation lives in `docs/`.

### `0dte-flow-lab/pyproject.toml`

Python packaging and dependency configuration.

Current responsibilities:

- Defines the distribution name as `odte-flow-lab`.
- Sets version `0.1.0`.
- Requires Python `>=3.10`.
- Declares runtime dependencies:
  - `duckdb`
  - `httpx`
  - `jupyter`
  - `pandas`
  - `plotly`
  - `pyarrow`
  - `python-dotenv`
- Declares optional `polars` support.
- Tells setuptools to find packages under `src`.

Current caveat:

- The package include rule still says `include = ["odte_flow_lab*"]`, but the current source files are directly under `src/`, not under `src/odte_flow_lab/`.
- If the flattened layout is intentional, this file should be adjusted later.
- If `odte_flow_lab` remains the intended package name, the source files should be moved back under `src/odte_flow_lab/`.

Editable install command:

```bash
cd 0dte-flow-lab
.venv/bin/python -m pip install -e .
```

### `0dte-flow-lab/.env.example`

Template for local configuration and secrets.

Current variables:

- `MASSIVE_API_KEY`: API key used by the Massive REST client.
- `ODTE_FLOW_LAB_DATA_DIR`: local data directory, defaulting to `data`.

Copy this file to `.env` before running live ingestion:

```bash
cd 0dte-flow-lab
cp .env.example .env
```

The real `.env` should not be committed.

---

## Source Files

### `0dte-flow-lab/src/__init__.py`

Current root initializer for the refactored source tree.

It defines:

```python
__version__ = "0.1.0"
```

Current caveat:

- In a conventional `src` layout, `src/` is not itself the package name. Usually a real package directory lives under `src/`, such as `src/odte_flow_lab/`.
- This file may be a temporary artifact of the flattening refactor.

### `0dte-flow-lab/src/config.py`

Central runtime configuration module.

Main responsibilities:

- Loads `.env` through `python-dotenv`.
- Resolves `PROJECT_ROOT`.
- Reads `ODTE_FLOW_LAB_DATA_DIR`.
- Reads `MASSIVE_API_KEY`.
- Defines a frozen `Settings` dataclass for shared configuration.

Important settings:

- `project_root`: resolved project path.
- `data_dir`: root local data directory.
- `raw_dir`: `data/raw`.
- `parquet_dir`: `data/parquet`.
- `duckdb_path`: `data/duckdb/flowlab.duckdb`.
- `massive_api_key`: Massive API key or `None`.

Current caveat:

- Because this file now lives at `src/config.py`, `PROJECT_ROOT = Path(__file__).resolve().parents[2]` resolves two levels above `src/config.py`, which points to the broader repository root rather than `0dte-flow-lab/`.
- If the lab data should remain under `0dte-flow-lab/data`, this path logic should be reviewed later.

---

## Data Modules

### `0dte-flow-lab/src/data/__init__.py`

Package marker for data ingestion and data-lake helpers.

It contains only a docstring and no runtime logic.

Its role is to make the `data` folder importable when the current source layout is on `PYTHONPATH`.

### `0dte-flow-lab/src/data/calendars.py`

Lightweight date helper module for the first ingestion pass.

Functions:

- `weekday_dates(start, end)`: returns weekdays in an inclusive date range.
- `recent_weekdays(end, count)`: returns the most recent `count` weekdays ending at `end`.

Behavior:

- Excludes Saturdays and Sundays.
- Does not yet know about market holidays.
- Does not yet know about market half-days.

This is intentionally simple for v0. Missing holiday/half-day handling is expected to show up in the data quality notebook through unusual row counts.

### `0dte-flow-lab/src/data/duckdb_catalog.py`

DuckDB catalog helper module for the local Parquet lake.

Main responsibilities:

- Opens the local DuckDB file.
- Creates or refreshes the `underlying_1m` view.
- Reads Parquet files from `data/parquet/underlying_1m/**/*.parquet`.
- Uses Hive partitioning so path segments like `symbol=SPY` and `date=2026-04-30` become queryable fields.
- Creates an empty `underlying_1m` view when no Parquet files exist yet.

Important symbols:

- `UNDERLYING_VIEW_NAME = "underlying_1m"`
- `underlying_glob(data_dir)`
- `connect(read_only=False)`
- `register_underlying_view(connection, data_dir=None)`
- `initialize_catalog()`
- `main()`

Current caveat:

- The file still imports `from odte_flow_lab.config import get_settings`, but the current source tree no longer contains `src/odte_flow_lab/config.py`.
- If the flattened layout is intended, this import should eventually become compatible with the new layout.

CLI intent:

```bash
cd 0dte-flow-lab
.venv/bin/python -m odte_flow_lab.data.duckdb_catalog --print-path
```

This command reflects the old package path and may need to change after the refactor is finalized.

### `0dte-flow-lab/src/data/ingest_underlying.py`

Rolling ingestion script for SPY/QQQ 1-minute underlying bars.

Main responsibilities:

- Parses CLI arguments:
  - `--symbols`
  - `--start`
  - `--end`
  - `--lookback-days`
  - `--force`
- Reads settings from `config.py`.
- Requires `MASSIVE_API_KEY`.
- Selects dates using `weekday_dates` or `recent_weekdays`.
- Fetches one symbol/date at a time through `MassiveClient`.
- Saves raw Massive API responses.
- Normalizes Massive aggregate bars into the `underlying_1m` lake schema.
- Writes partitioned Parquet.
- Refreshes the DuckDB catalog after ingestion.

Important symbols:

- `DEFAULT_SYMBOLS = ("SPY", "QQQ")`
- `IngestionResult`
- `parse_args()`
- `selected_dates(args, today=None)`
- `ingest_symbol_date(...)`
- `run(args)`
- `main()`

Current caveat:

- The file still imports from `odte_flow_lab.*`, while the files currently live directly under `src/`.
- Its CLI example still depends on the old package path until packaging/imports are reconciled.

Intended CLI shape:

```bash
cd 0dte-flow-lab
.venv/bin/python -m odte_flow_lab.data.ingest_underlying --symbols SPY QQQ --lookback-days 20
```

### `0dte-flow-lab/src/data/lake.py`

Parquet data-lake helper module for underlying 1-minute aggregate bars.

Main responsibilities:

- Defines canonical `underlying_1m` column ordering.
- Builds raw JSON paths.
- Builds partitioned Parquet paths.
- Saves raw Massive responses.
- Normalizes Massive response payloads into pandas dataframes.
- Writes normalized data to Parquet.

Canonical `underlying_1m` columns:

```text
symbol
bar_start_utc
bar_start_et
trade_date
timeframe
open
high
low
close
volume
vwap
transactions
adjusted
source
request_id
inserted_at_utc
```

Important symbols:

- `UNDERLYING_1M_COLUMNS`
- `raw_response_path(data_dir, symbol, trade_date)`
- `underlying_partition_dir(data_dir, symbol, trade_date)`
- `underlying_partition_path(data_dir, symbol, trade_date)`
- `save_raw_response(payload, data_dir, symbol, trade_date)`
- `normalize_underlying_1m(payload, symbol, trade_date, inserted_at_utc=None)`
- `write_underlying_partition(frame, data_dir, symbol, trade_date, force=False)`

Parquet write path:

```python
frame[UNDERLYING_1M_COLUMNS].to_parquet(path, engine="pyarrow", index=False)
```

`pyarrow` remains a project dependency, but this file does not import `pyarrow` directly.

### `0dte-flow-lab/src/data/massive_client.py`

HTTP client for Massive stock aggregate bars.

Main responsibilities:

- Builds the Massive aggregates endpoint:

```text
/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from}/{to}
```

- Defaults to 1-minute bars.
- Sends `adjusted`, `sort`, `limit`, and `apiKey`.
- Handles `next_url` pagination.
- Retries transient HTTP failures:
  - `429`
  - `500`
  - `502`
  - `503`
  - `504`
- Combines paginated API results into one payload.

Important symbols:

- `MassiveClient`
- `MassiveClient.fetch_stock_aggregates(...)`
- `MassiveClient._get_json(...)`
- `MassiveClient._sleep_before_retry(...)`
- `MassiveClient._with_api_key(...)`

This file should stay focused on API behavior. It should not know about DuckDB, notebooks, or Parquet layout.

---

## Indicator Modules

### `0dte-flow-lab/src/indicators/__init__.py`

Package marker for indicator calculations.

It contains only a docstring and no runtime logic.

### `0dte-flow-lab/src/indicators/regular_vwap.py`

Regular intraday VWAP reconstruction module.

Main function:

- `add_regular_vwap(frame, group_cols=("symbol", "trade_date"), ...)`

What it does:

- Validates required columns.
- Computes typical price:

```text
typical_price = (high + low + close) / 3
```

- Computes cumulative price-volume by group.
- Computes cumulative volume by group.
- Adds `regular_vwap`.

VWAP formula:

```text
regular_vwap = cumulative_sum(typical_price * volume) / cumulative_sum(volume)
```

This is the first indicator slice. Future C-VWAP, P-VWAP, and O-VWAP modules should live near this file once option-side data exists.

---

## Notebooks

### `0dte-flow-lab/notebooks/01_data_check.ipynb`

Data quality notebook for ingested `underlying_1m` bars.

Main responsibilities:

- Opens DuckDB.
- Registers or refreshes the `underlying_1m` view.
- Shows row counts by symbol/date.
- Shows first and last bar timestamps.
- Counts regular-session rows.
- Detects duplicate `symbol + bar_start_utc` rows.
- Flags regular-session days whose row count differs from 390.
- Checks OHLC consistency.
- Checks bad/null volume.
- Checks null Massive VWAP values.

Current caveat:

- The notebook still imports `odte_flow_lab.*`. If the flattened source layout is the final direction, notebook imports should be updated later.

### `0dte-flow-lab/notebooks/02_rebuild_vwap.ipynb`

First indicator reconstruction notebook.

Main responsibilities:

- Opens DuckDB.
- Registers or refreshes the `underlying_1m` view.
- Selects a symbol/day from available data.
- Loads regular-session bars.
- Calls `add_regular_vwap(...)`.
- Displays close, Massive bar VWAP, and reconstructed regular VWAP.
- Plots candles plus regular VWAP with Plotly.

Current caveat:

- The notebook still imports `odte_flow_lab.*`. If the flattened source layout is the final direction, notebook imports should be updated later.

---

## Local Data And Generated Artifacts

### `0dte-flow-lab/data/duckdb/flowlab.duckdb`

Local DuckDB database file.

It stores DuckDB catalog state and views, especially the `underlying_1m` view. The Parquet files remain the main data lake source of truth.

This file is local data and should usually stay out of git.

### `0dte-flow-lab/src/egg-info/`

Generated Python packaging metadata from an editable install.

Current files include:

- `PKG-INFO`
- `SOURCES.txt`
- `requires.txt`
- `top_level.txt`
- `dependency_links.txt`

Current caveat:

- The metadata still references `odte_flow_lab`, including `top_level.txt`.
- This may be stale after the source flattening refactor.
- It should not be hand-edited; regenerate it through packaging once the intended import layout is finalized.

---

## How The Files Are Intended To Work Together

```text
.env / .env.example
  -> src/config.py
  -> src/data/massive_client.py
  -> src/data/ingest_underlying.py
  -> src/data/lake.py
  -> data/raw + data/parquet
  -> src/data/duckdb_catalog.py
  -> notebooks/01_data_check.ipynb
  -> src/indicators/regular_vwap.py
  -> notebooks/02_rebuild_vwap.ipynb
```

In short:

- `config.py` resolves paths and secrets.
- `massive_client.py` fetches API data.
- `ingest_underlying.py` orchestrates ingestion.
- `lake.py` normalizes and writes local data.
- `duckdb_catalog.py` exposes Parquet through DuckDB.
- `01_data_check.ipynb` validates ingested data.
- `regular_vwap.py` computes regular VWAP.
- `02_rebuild_vwap.ipynb` visualizes price plus VWAP.

---

## Follow-Up To Consider

The code layout and import path are currently out of sync. Pick one direction:

1. Restore package layout:

```text
0dte-flow-lab/src/odte_flow_lab/
  config.py
  data/
  indicators/
```

and keep imports like:

```python
from odte_flow_lab.config import get_settings
```

1. Keep flattened layout:

```text
0dte-flow-lab/src/
  config.py
  data/
  indicators/
```

and update imports, notebooks, and `pyproject.toml` accordingly.

The first option is more conventional for a packaged Python project.