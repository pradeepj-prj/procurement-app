from __future__ import annotations

from app.db.backend import DataBackend


def get_backend() -> DataBackend:
    """Return the configured DataBackend implementation.

    Reads ``settings.graph_backend`` to decide:
    - ``"networkx"`` → local CSV-backed graph (dev)
    - ``"hana"``     → SAP HANA Cloud (production, subplan 03)
    """
    from app.config import settings

    if settings.graph_backend == "networkx":
        from app.db.networkx_backend import NetworkXBackend

        return NetworkXBackend()

    if settings.graph_backend == "hana":
        raise NotImplementedError(
            "HANABackend is not yet implemented (see subplan 03)."
        )

    raise ValueError(f"Unknown graph_backend: {settings.graph_backend!r}")


__all__ = ["DataBackend", "get_backend"]
