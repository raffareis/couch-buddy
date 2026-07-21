"""Cruza GameState + guia do mapa + progresso manual num ViewModel para a UI."""
from __future__ import annotations

import re

from couch_buddy.brain.progress import ProgressStore
from couch_buddy.knowledge.library import GuideLibrary
from couch_buddy.state.models import GameState


def _norm_quest(name: str) -> str:
    name = re.sub(r"_?quest$", "", name, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", name.lower())


def quest_display_name(internal: str) -> str:
    """``HuntingGrounds_quest`` → ``Hunting Grounds``."""
    base = re.sub(r"_?quest$", "", internal, flags=re.IGNORECASE).replace("_", " ")
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", base).strip()


def _quest_states_by_name(
    state: GameState, blueprint_names: dict[str, dict]
) -> dict[str, str]:
    """Nome normalizado da quest -> estado no save (só quests nomeáveis)."""
    result: dict[str, str] = {}
    for quest in state.quests:
        entry = blueprint_names.get(quest.blueprint)
        if entry and entry.get("type") == "BlueprintQuest":
            result[_norm_quest(entry["name"])] = quest.state
    return result


def build_view(
    state: GameState | None,
    library: GuideLibrary,
    progress: ProgressStore,
    blueprint_names: dict[str, dict] | None = None,
) -> dict:
    if state is None:
        return {
            "area_name": None,
            "chapter": None,
            "save_name": None,
            "saved_at": None,
            "guide": None,
            "quests_ativas": [],
            "unknown_area": False,
        }

    names = blueprint_names or {}
    quest_states = _quest_states_by_name(state, names)

    guide = library.find(state.area_name or "")
    guide_view = None
    if guide is not None:
        slug = library.slug_of(guide)
        ticks = progress.get(state.game_id)
        steps = []
        for step in guide.steps:
            key = f"{slug}:{step.order}"
            auto_done = (
                step.type == "quest_step"
                and step.quest is not None
                and quest_states.get(_norm_quest(step.quest)) == "Completed"
            )
            steps.append(
                {
                    **step.model_dump(),
                    "step_key": key,
                    "done": ticks.get(key, False) or auto_done,
                    "auto": auto_done,
                }
            )
        guide_view = {
            "slug": slug,
            "area_name": guide.area_name,
            "act": guide.act,
            "steps": steps,
        }

    quests_ativas = sorted(
        quest_display_name(names[q.blueprint]["name"])
        for q in state.quests
        if q.state == "Started"
        and names.get(q.blueprint, {}).get("type") == "BlueprintQuest"
    )

    return {
        "area_name": state.area_name or state.area_guid,
        "chapter": state.chapter,
        "save_name": state.save_name,
        "saved_at": state.saved_at.isoformat() if state.saved_at else None,
        "guide": guide_view,
        "quests_ativas": quests_ativas,
        "unknown_area": state.area_name is None,
    }
