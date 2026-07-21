"""Estado central do companion: último GameState + fan-out para a UI."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from couch_buddy.brain.progress import ProgressStore
from couch_buddy.brain.reconciler import build_view
from couch_buddy.knowledge.library import GuideLibrary
from couch_buddy.state.models import GameState
from couch_buddy.state.save_parser import parse_save

log = logging.getLogger(__name__)


class Companion:
    def __init__(
        self,
        library: GuideLibrary,
        progress: ProgressStore,
        guid_map: dict[str, str],
    ) -> None:
        self._library = library
        self._progress = progress
        self._guid_map = guid_map
        self._state: GameState | None = None
        self._subscribers: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @property
    def state(self) -> GameState | None:
        return self._state

    def view(self) -> dict:
        return build_view(self._state, self._library, self._progress)

    def on_save(self, path: Path) -> None:
        """Callback do watcher (thread própria): parseia e publica."""
        try:
            self._state = parse_save(path, self._guid_map)
        except Exception:
            log.exception("falha parseando %s; mantendo estado anterior", path)
            return
        log.info(
            "save %s → área %s (cap. %s)",
            path.name,
            self._state.area_name or self._state.area_guid,
            self._state.chapter,
        )
        self._publish()

    def tick(self, step_key: str, done: bool) -> dict:
        game_id = self._state.game_id if self._state else "default"
        self._progress.set(game_id, step_key, done)
        view = self.view()
        self._publish()
        return view

    def learn_area(self, name: str) -> dict:
        """Aprende o nome da área atual (banner de área desconhecida)."""
        if self._state is not None:
            self._guid_map[self._state.area_guid] = name
            self._state.area_name = name
            self._publish()
        return self.view()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def _publish(self) -> None:
        if self._loop is None:
            return
        view = self.view()
        for queue in list(self._subscribers):
            self._loop.call_soon_threadsafe(queue.put_nowait, view)
