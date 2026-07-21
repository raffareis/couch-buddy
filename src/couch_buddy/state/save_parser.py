"""Parser dos saves .zks (ZIP com JSON) do Rogue Trader.

Lê apenas header.json e player.json — o resto do arquivo (~10MB) não é
descompactado. O nome da área é resolvido pelo guid_map e, na falta dele,
derivado dos filenames internos do próprio save (os .fog carregam o nome
da cena: ``<guid>.<Cena>_StaticForArt.fog``).
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from couch_buddy.state.models import GameState, ObjectiveState, QuestState

_GUID = "[0-9a-f]{32}"
_FOG_RE = re.compile(rf"^({_GUID})\.(.+?)\.fog$")
_MECH_RE = re.compile(rf"^({_GUID})(.+?)Mechanics\.json$")
_STATIC_SUFFIX_RE = re.compile(r"_?[Ss]tatic.*$")


def _common_token_prefix(candidates: list[str]) -> str:
    """Maior prefixo comum alinhado em tokens separados por ``_``."""
    if not candidates:
        return ""
    if len(candidates) == 1:
        return candidates[0]
    tokens = [c.split("_") for c in candidates]
    prefix: list[str] = []
    for parts in zip(*tokens):
        if all(p == parts[0] for p in parts):
            prefix.append(parts[0])
        else:
            break
    if prefix:
        return "_".join(prefix)
    return candidates[0]


def derive_area_names(namelist: list[str]) -> dict[str, str]:
    """Extrai ``guid -> nome de cena`` dos filenames internos do save."""
    candidates: dict[str, list[str]] = {}
    for name in namelist:
        if m := _FOG_RE.match(name):
            guid, scene = m.group(1), _STATIC_SUFFIX_RE.sub("", m.group(2))
        elif m := _MECH_RE.match(name):
            guid, scene = m.group(1), m.group(2).rstrip("_")
        else:
            continue
        if scene:
            candidates.setdefault(guid, [])
            if scene not in candidates[guid]:
                candidates[guid].append(scene)
    return {
        guid: name
        for guid, scenes in candidates.items()
        if (name := _common_token_prefix(scenes).strip("_"))
    }


def _parse_quests(player: dict) -> list[QuestState]:
    facts = player.get("m_QuestBook", {}).get("Facts", {}).get("m_Facts", [])
    quests = []
    for fact in facts:
        if not isinstance(fact, dict) or "Blueprint" not in fact:
            continue
        objectives = [
            ObjectiveState(
                blueprint=o.get("Blueprint", ""),
                state=o.get("m_State", "Unknown"),
                order=o.get("Order"),
            )
            for o in fact.get("PersistentObjectives", [])
            if isinstance(o, dict)
        ]
        quests.append(
            QuestState(
                blueprint=fact["Blueprint"],
                state=fact.get("m_State", "Unknown"),
                objectives=objectives,
            )
        )
    return quests


def parse_save(path: Path, guid_map: dict[str, str]) -> GameState:
    with zipfile.ZipFile(path) as z:
        header = json.loads(z.read("header.json"))
        player = json.loads(z.read("player.json"))
        derived = derive_area_names(z.namelist())

    area_guid = player["CurrentArea"]
    return GameState(
        area_guid=area_guid,
        area_name=guid_map.get(area_guid) or derived.get(area_guid),
        chapter=player.get("Chapter", 0),
        quests=_parse_quests(player),
        save_id=header.get("SaveId", ""),
        game_id=header.get("GameId", ""),
        save_name=header.get("Name", path.stem),
        saved_at=header.get("SystemSaveTime"),
    )
