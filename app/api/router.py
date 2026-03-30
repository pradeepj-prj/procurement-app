from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Procurement GenAI Q&A", version="2.0.0")


@app.get("/")
async def root():
    return {"status": "ok"}
