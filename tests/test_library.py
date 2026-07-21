import json

from couch_buddy.knowledge.library import GuideLibrary


def _write_guide(maps_dir, slug, area_name, aliases):
    maps_dir.mkdir(parents=True, exist_ok=True)
    guide = {
        "area_name": area_name,
        "aliases": aliases,
        "act": 2,
        "sources": [],
        "steps": [
            {"order": 1, "type": "item", "title": "Item de teste", "details": ""}
        ],
    }
    (maps_dir / f"{slug}.json").write_text(json.dumps(guide))


def test_find_exato_alias_e_normalizacao(tmp_path):
    maps = tmp_path / "maps"
    _write_guide(maps, "footfall-crematory", "Footfall Crematory", ["Crematorium"])
    _write_guide(maps, "administratum", "Administratum", ["AdministratumPalace"])
    lib = GuideLibrary(maps)

    assert lib.find("Footfall_Crematory").area_name == "Footfall Crematory"
    assert lib.find("crematorium").area_name == "Footfall Crematory"
    assert lib.find("AdministratumPalace").area_name == "Administratum"
    assert lib.find("Inexistente") is None
    assert lib.find("") is None


def test_find_por_prefixo(tmp_path):
    maps = tmp_path / "maps"
    _write_guide(maps, "footfall", "Footfall", [])
    lib = GuideLibrary(maps)
    # área do save é mais específica que o guia
    assert lib.find("FootfallSlums_MutantsLair").area_name == "Footfall"
