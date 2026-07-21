"""Persistência dos ticks manuais por campanha (game_id do save)."""
from __future__ import annotations

import json
from pathlib import Path


class ProgressStore:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def _path(self, game_id: str) -> Path:
        return self._data_dir / f"{game_id or 'default'}.json"

    def get(self, game_id: str) -> dict[str, bool]:
        path = self._path(game_id)
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def set(self, game_id: str, step_key: str, done: bool) -> None:
        progress = self.get(game_id)
        if done:
            progress[step_key] = True
        else:
            progress.pop(step_key, None)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._path(game_id).write_text(
            json.dumps(progress, ensure_ascii=False, indent=1, sort_keys=True)
        )
