"""Carrega os guias curados e casa a área do save com o guia certo."""
from __future__ import annotations

import json
import re
from pathlib import Path

from couch_buddy.knowledge.schema import MapGuide


def _norm(name: str) -> str:
    return re.sub(r"[\s_\-]+", "", name).lower()


class GuideLibrary:
    def __init__(self, maps_dir: Path) -> None:
        self._maps_dir = maps_dir
        self._guides: dict[str, MapGuide] = {}  # slug -> guide
        self._index: dict[str, str] = {}  # nome normalizado -> slug
        self.reload()

    def reload(self) -> None:
        self._guides.clear()
        self._index.clear()
        if not self._maps_dir.exists():
            return
        for path in sorted(self._maps_dir.glob("*.json")):
            guide = MapGuide.model_validate(json.loads(path.read_text()))
            slug = path.stem
            self._guides[slug] = guide
            for name in [guide.area_name, *guide.aliases]:
                self._index.setdefault(_norm(name), slug)

    def slug_of(self, guide: MapGuide) -> str:
        for slug, g in self._guides.items():
            if g is guide:
                return slug
        raise ValueError("guia não pertence à biblioteca")

    def find(self, area_name: str) -> MapGuide | None:
        """Casa por nome/alias; tolera prefixo (``Footfall_Crematory`` acha
        o guia cujo nome normalizado é prefixo do nome da área, e vice-versa)."""
        if not area_name:
            return None
        norm = _norm(area_name)
        if slug := self._index.get(norm):
            return self._guides[slug]
        candidates = [
            (len(key), slug)
            for key, slug in self._index.items()
            if key.startswith(norm) or norm.startswith(key)
        ]
        if candidates:
            _, slug = max(candidates)
            return self._guides[slug]
        return None

    def all(self) -> list[MapGuide]:
        return list(self._guides.values())
