import json
from datetime import datetime

from couch_buddy.brain.progress import ProgressStore
from couch_buddy.brain.reconciler import build_view
from couch_buddy.knowledge.library import GuideLibrary
from couch_buddy.state.models import GameState


def _state(area_name):
    return GameState(
        area_guid="48cdcd77ce194f07bb55003797f321d3",
        area_name=area_name,
        chapter=2,
        quests=[],
        save_id="s1",
        game_id="g1",
        save_name="Administratum -New Save",
        saved_at=datetime(2026, 3, 5, 3, 9),
    )


def _library(tmp_path):
    maps = tmp_path / "maps"
    maps.mkdir()
    (maps / "administratum.json").write_text(
        json.dumps(
            {
                "area_name": "Administratum",
                "aliases": ["AdministratumPalace"],
                "act": 2,
                "sources": [],
                "steps": [
                    {"order": 1, "type": "item", "title": "Pegar relíquia"},
                    {"order": 2, "type": "decision", "title": "Escolher facção"},
                ],
            }
        )
    )
    return GuideLibrary(maps)


def test_view_com_guia_e_ticks(tmp_path):
    library = _library(tmp_path)
    progress = ProgressStore(tmp_path / "progress")
    progress.set("g1", "administratum:1", True)

    view = build_view(_state("AdministratumPalace"), library, progress)
    assert view["guide"]["slug"] == "administratum"
    steps = view["guide"]["steps"]
    assert steps[0]["done"] is True and steps[1]["done"] is False
    assert steps[0]["step_key"] == "administratum:1"
    assert view["unknown_area"] is False


def test_view_area_sem_guia(tmp_path):
    view = build_view(
        _state("LugarIgnoto"), _library(tmp_path), ProgressStore(tmp_path / "p")
    )
    assert view["guide"] is None
    assert view["area_name"] == "LugarIgnoto"


def test_view_area_desconhecida(tmp_path):
    view = build_view(
        _state(None), _library(tmp_path), ProgressStore(tmp_path / "p")
    )
    assert view["unknown_area"] is True
    assert view["area_name"] == "48cdcd77ce194f07bb55003797f321d3"


def test_auto_check_por_quest_do_save(tmp_path):
    from couch_buddy.state.models import QuestState

    library = _library(tmp_path)
    maps = tmp_path / "maps"
    (maps / "administratum.json").write_text(
        json.dumps(
            {
                "area_name": "Administratum",
                "aliases": ["AdministratumPalace"],
                "act": 2,
                "sources": [],
                "steps": [
                    {
                        "order": 1,
                        "type": "quest_step",
                        "title": "Concluir Hunting Grounds",
                        "quest": "Hunting Grounds",
                    },
                    {
                        "order": 2,
                        "type": "quest_step",
                        "title": "Avançar outra quest",
                        "quest": "Other Quest",
                    },
                ],
            }
        )
    )
    library.reload()

    state = _state("AdministratumPalace")
    state.quests = [
        QuestState(blueprint="aaa", state="Completed"),
        QuestState(blueprint="bbb", state="Started"),
    ]
    names = {
        "aaa": {"name": "HuntingGrounds_quest", "type": "BlueprintQuest"},
        "bbb": {"name": "OtherQuest_quest", "type": "BlueprintQuest"},
    }
    view = build_view(state, library, ProgressStore(tmp_path / "p"), names)
    steps = view["guide"]["steps"]
    assert steps[0]["done"] is True and steps[0]["auto"] is True
    assert steps[1]["done"] is False
    assert view["quests_ativas"] == ["Other Quest"]


def test_progress_roundtrip(tmp_path):
    store = ProgressStore(tmp_path / "p")
    store.set("g1", "x:1", True)
    store.set("g1", "x:2", True)
    store.set("g1", "x:1", False)
    assert store.get("g1") == {"x:2": True}
