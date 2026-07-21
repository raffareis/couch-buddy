"""Modelos do estado do jogo extraído dos saves."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ObjectiveState(BaseModel):
    blueprint: str
    state: str
    order: int | None = None


class QuestState(BaseModel):
    blueprint: str
    state: str
    objectives: list[ObjectiveState] = []


class GameState(BaseModel):
    area_guid: str
    area_name: str | None = None
    chapter: int
    quests: list[QuestState] = []
    save_id: str
    game_id: str
    save_name: str
    saved_at: datetime | None = None
