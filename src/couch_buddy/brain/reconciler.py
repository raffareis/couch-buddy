"""Cruza GameState + guia do mapa + progresso manual num ViewModel para a UI."""
from __future__ import annotations

from couch_buddy.brain.progress import ProgressStore
from couch_buddy.knowledge.library import GuideLibrary
from couch_buddy.state.models import GameState


def build_view(
    state: GameState | None,
    library: GuideLibrary,
    progress: ProgressStore,
) -> dict:
    if state is None:
        return {
            "area_name": None,
            "chapter": None,
            "save_name": None,
            "saved_at": None,
            "guide": None,
            "unknown_area": False,
        }

    guide = library.find(state.area_name or "")
    guide_view = None
    if guide is not None:
        slug = library.slug_of(guide)
        ticks = progress.get(state.game_id)
        guide_view = {
            "slug": slug,
            "area_name": guide.area_name,
            "act": guide.act,
            "steps": [
                {
                    **step.model_dump(),
                    "step_key": (key := f"{slug}:{step.order}"),
                    "done": ticks.get(key, False),
                }
                for step in guide.steps
            ],
        }

    return {
        "area_name": state.area_name or state.area_guid,
        "chapter": state.chapter,
        "save_name": state.save_name,
        "saved_at": state.saved_at.isoformat() if state.saved_at else None,
        "guide": guide_view,
        "unknown_area": state.area_name is None,
    }
