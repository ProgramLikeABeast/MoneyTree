"""Runtime configuration for local 0DTE FlowLab research workflows."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Resolved paths and credentials used by data scripts."""

    project_root: Path
    data_dir: Path
    massive_api_key: str | None

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def parquet_dir(self) -> Path:
        return self.data_dir / "parquet"

    @property
    def duckdb_path(self) -> Path:
        return self.data_dir / "duckdb" / "flowlab.duckdb"


def get_settings() -> Settings:
    data_dir_value = os.getenv("ODTE_FLOW_LAB_DATA_DIR", "data")
    data_dir = Path(data_dir_value)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir

    return Settings(
        project_root=PROJECT_ROOT,
        data_dir=data_dir,
        massive_api_key=os.getenv("MASSIVE_API_KEY"),
    )
