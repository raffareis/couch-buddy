"""Bootstrap do guid_map.json a partir dos filenames internos de todos os saves.

Entradas aprendidas manualmente (``"manual": true``) nunca são sobrescritas.
Formato: ``{guid: {"name": str, "manual": bool}}``.

Uso: .venv/bin/python tools/build_guid_map.py [--saves-dir D] [--out F]
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from couch_buddy.state.save_parser import derive_area_names  # noqa: E402

DEFAULT_SAVES = Path(
    "/home/raffareis/Storage/SteamLibrary/steamapps/compatdata/2186680/pfx/drive_c"
    "/users/steamuser/AppData/LocalLow/Owlcat Games/Warhammer 40000 Rogue Trader"
    "/Saved Games"
)
DEFAULT_OUT = Path(__file__).parent.parent / "data/games/rogue-trader/guid_map.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saves-dir", type=Path, default=DEFAULT_SAVES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    existing: dict[str, dict] = {}
    if args.out.exists():
        existing = json.loads(args.out.read_text())

    derived: dict[str, str] = {}
    saves = sorted(args.saves_dir.glob("*.zks"))
    for save in saves:
        try:
            with zipfile.ZipFile(save) as z:
                for guid, name in derive_area_names(z.namelist()).items():
                    # nome mais curto = prefixo comum de mais cenas = nome
                    # da área (não de uma sub-cena específica)
                    if guid not in derived or len(name) < len(derived[guid]):
                        derived[guid] = name
        except zipfile.BadZipFile:
            print(f"ignorando save corrompido: {save.name}", file=sys.stderr)

    merged = dict(existing)
    for guid, name in derived.items():
        if guid in merged and merged[guid].get("manual"):
            continue
        merged[guid] = {"name": name, "manual": False}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(merged, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"{len(saves)} saves lidos, {len(merged)} áreas em {args.out}")


if __name__ == "__main__":
    main()
