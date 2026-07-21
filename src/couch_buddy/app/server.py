"""Servidor FastAPI: página estática + estado via REST/WebSocket."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from couch_buddy.app.companion import Companion

STATIC_DIR = Path(__file__).parent / "static"


class TickRequest(BaseModel):
    step_key: str
    done: bool


class LearnAreaRequest(BaseModel):
    name: str


def create_app(companion: Companion) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        companion.bind_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(title="couch-buddy", lifespan=lifespan)

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/state")
    async def state() -> dict:
        return companion.view()

    @app.post("/api/tick")
    async def tick(req: TickRequest) -> dict:
        return companion.tick(req.step_key, req.done)

    @app.post("/api/learn-area")
    async def learn_area(req: LearnAreaRequest) -> dict:
        return companion.learn_area(req.name)

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = companion.subscribe()
        try:
            await websocket.send_json(companion.view())
            while True:
                view = await queue.get()
                await websocket.send_json(view)
        except WebSocketDisconnect:
            pass
        finally:
            companion.unsubscribe(queue)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
