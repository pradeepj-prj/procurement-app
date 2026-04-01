from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI) -> None:
    """Add CORS middleware to allow the React frontend to talk to this backend.

    Default origins cover common React dev servers (Vite at 5173, CRA at 3000).
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
