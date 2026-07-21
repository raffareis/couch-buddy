import pytest
from pydantic import ValidationError

from couch_buddy.knowledge.schema import MapGuide

VALID = {
    "area_name": "Footfall_Crematory",
    "aliases": ["Crematorium"],
    "act": 2,
    "sources": [{"url": "https://example.com/guia", "title": "Guia"}],
    "steps": [
        {
            "order": 1,
            "type": "item",
            "title": "Pegar o servo-skull",
            "details": "Atrás do altar, skill check de Awareness.",
            "quest": None,
            "missable": True,
            "spoiler": "low",
            "source_url": "https://example.com/guia",
        }
    ],
}


def test_map_guide_valido():
    guide = MapGuide.model_validate(VALID)
    assert guide.steps[0].missable is True


def test_map_guide_type_invalido():
    bad = {**VALID, "steps": [{**VALID["steps"][0], "type": "loot"}]}
    with pytest.raises(ValidationError):
        MapGuide.model_validate(bad)
