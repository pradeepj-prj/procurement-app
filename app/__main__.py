"""Entry point for `python -m app`."""

from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Procurement GenAI Q&A backend")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    args = parser.parse_args()

    uvicorn.run("app.api.router:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
