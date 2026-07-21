import json
import zipfile
from pathlib import Path

import pytest

from couch_buddy.state.save_parser import derive_area_names, parse_save

FIXTURES = Path(__file__).parent / "fixtures"


def _make_zks(tmp_path: Path) -> Path:
    """Monta um .zks mínimo com os JSONs reais reduzidos + namelist real."""
    reduced = json.loads((FIXTURES / "player_reduced.json").read_text())
    path = tmp_path / "Manual_79_Administratum.zks"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("header.json", (FIXTURES / "header.json").read_text())
        z.writestr("player.json", json.dumps(reduced))
        for name in (FIXTURES / "namelist.txt").read_text().splitlines():
            if name not in ("header.json", "player.json") and name.endswith(".fog"):
                z.writestr(name, b"")
    return path


def test_parse_save_estado_basico(tmp_path):
    state = parse_save(_make_zks(tmp_path), guid_map={})
    assert state.area_guid == "48cdcd77ce194f07bb55003797f321d3"
    assert state.chapter == 2
    assert state.save_name.startswith("Administratum")
    assert len(state.quests) == 12
    assert state.quests[0].state in ("Completed", "Started", "Active", "Failed")
    assert state.quests[0].objectives, "quest deve ter objectives"


def test_area_name_derivado_do_fog(tmp_path):
    state = parse_save(_make_zks(tmp_path), guid_map={})
    assert state.area_name == "AdministratumPalace"


def test_guid_map_tem_precedencia(tmp_path):
    state = parse_save(
        _make_zks(tmp_path),
        guid_map={"48cdcd77ce194f07bb55003797f321d3": "Administratum (Dargonus)"},
    )
    assert state.area_name == "Administratum (Dargonus)"


def test_derive_area_names_prefixo_comum():
    names = derive_area_names(
        [
            "1e35b94dbf544e289cf6139e621dd70b.Footfall_Crematory_StaticForArt.fog",
            "1e35b94dbf544e289cf6139e621dd70b.Footfall_Warehouse_StaticForArt.fog",
            "697811fcf1394f96828ac36be4706c42.VoidshipLowerDecks_Static_for_Art.fog",
        ]
    )
    assert names["1e35b94dbf544e289cf6139e621dd70b"] == "Footfall"
    assert names["697811fcf1394f96828ac36be4706c42"] == "VoidshipLowerDecks"


REAL_SAVE = Path(
    "/home/raffareis/Storage/SteamLibrary/steamapps/compatdata/2186680/pfx/drive_c"
    "/users/steamuser/AppData/LocalLow/Owlcat Games/Warhammer 40000 Rogue Trader"
    "/Saved Games/Manual_79_Administratum__New_Save__21_46_43.zks"
)


@pytest.mark.skipif(not REAL_SAVE.exists(), reason="save real indisponível")
def test_parse_save_real_completo():
    state = parse_save(REAL_SAVE, guid_map={})
    assert state.chapter == 2
    assert len(state.quests) > 50
    assert state.area_name == "AdministratumPalace"
