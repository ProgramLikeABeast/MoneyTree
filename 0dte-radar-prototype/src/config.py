"""Runtime configuration for the Phase 1 Moomoo data access."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Resolved settings for local Moomoo data access."""

    project_root: Path
    moomoo_host: str
    moomoo_port: int
    symbols: tuple[str, ...]
    data_mode: str


def get_settings() -> Settings:
    symbols = tuple[str, ...](
        symbol.strip()
        for symbol in os.getenv("SYMBOLS", "US.SPY,US.QQQ").split(",")
        if symbol.strip()
    )

    return Settings(
        project_root=PROJECT_ROOT,
        moomoo_host=os.getenv("MOOMOO_HOST", "127.0.0.1"),
        moomoo_port=int(os.getenv("MOOMOO_PORT", "11111")),
        symbols=symbols,
        data_mode=os.getenv("DATA_MODE", "auto"),
    )
