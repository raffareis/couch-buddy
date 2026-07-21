"""Schema dos guias estruturados por mapa."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, HttpUrl

StepType = Literal["item", "interaction", "quest_step", "decision", "combat_tip"]
SpoilerLevel = Literal["low", "medium", "high"]


class Source(BaseModel):
    url: str
    title: str = ""


class Step(BaseModel):
    order: int
    type: StepType
    title: str
    details: str = ""
    quest: str | None = None
    missable: bool = False
    spoiler: SpoilerLevel = "low"
    source_url: str = ""


class MapGuide(BaseModel):
    area_name: str
    aliases: list[str] = []
    act: int | None = None
    sources: list[Source] = []
    steps: list[Step] = []
