"""Runtime configuration for the Phase 1 Moomoo quote loop."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Resolved settings for local quote collection and dashboard refresh."""

    project_root: Path
    data_dir: Path
    moomoo_host: str
    moomoo_port: int
    symbols: tuple[str, ...]
    quote_interval_seconds: float
    plot_refresh_seconds: int
    data_mode: str

    @property
    def duckdb_path(self) -> Path:
        return self.data_dir / "duckdb" / "odte_radar.duckdb"


def get_settings() -> Settings:
    data_dir_value = os.getenv("ODTE_RADAR_DATA_DIR", "data")
    data_dir = Path(data_dir_value)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    symbols = tuple(
        symbol.strip()
        for symbol in os.getenv("SYMBOLS", "US.SPY,US.QQQ").split(",")
        if symbol.strip()
    )

    return Settings(
        project_root=PROJECT_ROOT,
        data_dir=data_dir,
        moomoo_host=os.getenv("MOOMOO_HOST", "127.0.0.1"),
        moomoo_port=int(os.getenv("MOOMOO_PORT", "11111")),
        symbols=symbols,
        quote_interval_seconds=float(os.getenv("QUOTE_INTERVAL_SECONDS", "2")),
        plot_refresh_seconds=int(os.getenv("PLOT_REFRESH_SECONDS", "120")),
        data_mode=os.getenv("DATA_MODE", "auto"),
    )
