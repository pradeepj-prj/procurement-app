from __future__ import annotations

from fastapi import Request

from app.db.backend import DataBackend


def get_backend(request: Request) -> DataBackend:
    """FastAPI dependency that returns the shared database backend.

    The backend is initialised during the app lifespan and stored on
    ``request.app.state.backend``.  Any endpoint can declare
    ``backend: DataBackend = Depends(get_backend)`` to receive it.
    """
    return request.app.state.backend
