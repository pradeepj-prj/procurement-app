from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def csv_dir() -> Path:
    """Resolve the CSV data directory, skipping if not available."""
    from app.config import settings

    path = Path(settings.csv_dir)
    if not path.exists() or not any(path.glob("*.csv")):
        pytest.skip(f"CSV data not found at {path}")
    return path


@pytest.fixture(scope="session")
def nx_backend(csv_dir: Path):
    """Provide a NetworkXBackend loaded with real CSV data."""
    from app.db.networkx_backend import NetworkXBackend

    return NetworkXBackend(csv_dir=str(csv_dir))
