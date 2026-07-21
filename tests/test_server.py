import json

from fastapi.testclient import TestClient

from couch_buddy.app.companion import Companion
from couch_buddy.app.server import create_app
from couch_buddy.brain.progress import ProgressStore
from couch_buddy.knowledge.library import GuideLibrary


def _companion(tmp_path):
    maps = tmp_path / "maps"
    maps.mkdir()
    (maps / "administratum.json").write_text(
        json.dumps(
            {
                "area_name": "AdministratumPalace",
                "aliases": [],
                "act": 2,
                "sources": [],
                "steps": [{"order": 1, "type": "item", "title": "Pegar relíquia"}],
            }
        )
    )
    return Companion(
        GuideLibrary(maps), ProgressStore(tmp_path / "progress"), guid_map={}
    )


def test_state_e_tick(tmp_path, monkeypatch):
    import tests.test_save_parser as tsp

    companion = _companion(tmp_path)
    client = TestClient(create_app(companion))

    companion.on_save(tsp._make_zks(tmp_path))

    view = client.get("/api/state").json()
    assert view["area_name"] == "AdministratumPalace"
    assert view["guide"]["steps"][0]["done"] is False

    view = client.post(
        "/api/tick", json={"step_key": "administratum:1", "done": True}
    ).json()
    assert view["guide"]["steps"][0]["done"] is True


def test_websocket_entrega_estado(tmp_path):
    client = TestClient(create_app(_companion(tmp_path)))
    with client.websocket_connect("/ws") as ws:
        view = ws.receive_json()
        assert "area_name" in view


def test_learn_area_persiste_manual(tmp_path):
    import tests.test_save_parser as tsp
    from couch_buddy.app.companion import Companion
    from couch_buddy.brain.progress import ProgressStore
    from couch_buddy.knowledge.library import GuideLibrary

    guid_map_path = tmp_path / "guid_map.json"
    companion = Companion(
        GuideLibrary(tmp_path / "maps"),
        ProgressStore(tmp_path / "progress"),
        guid_map={},
        guid_map_path=guid_map_path,
    )
    companion.on_save(tsp._make_zks(tmp_path))
    companion.learn_area("Administratum (Dargonus)")

    saved = json.loads(guid_map_path.read_text())
    entry = saved["48cdcd77ce194f07bb55003797f321d3"]
    assert entry == {"name": "Administratum (Dargonus)", "manual": True}
