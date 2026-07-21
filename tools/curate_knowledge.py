"""Valida e normaliza os JSONs brutos de walkthrough (raw/) para maps/.

- Valida contra o schema MapGuide (pydantic).
- Renumera ``order`` para 1..n mantendo a ordem original.
- Injeta aliases internos do jogo (internal_aliases.json: slug -> nomes de
  área como aparecem nos saves/blueprints), que fazem o casamento save↔guia.
- Slug do arquivo de saída = nome do arquivo bruto.
Uso: .venv/bin/python tools/curate_knowledge.py [--raw D] [--maps D]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pydantic import ValidationError  # noqa: E402

from couch_buddy.knowledge.schema import MapGuide  # noqa: E402

BASE = Path(__file__).parent.parent / "data/games/rogue-trader"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=BASE / "raw")
    ap.add_argument("--maps", type=Path, default=BASE / "maps")
    args = ap.parse_args()

    args.maps.mkdir(parents=True, exist_ok=True)
    aliases_path = BASE / "internal_aliases.json"
    internal_aliases: dict[str, list[str]] = (
        json.loads(aliases_path.read_text()) if aliases_path.exists() else {}
    )
    ok, failed = 0, []
    for path in sorted(args.raw.rglob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            guide = MapGuide.model_validate(json.loads(path.read_text()))
        except (ValidationError, json.JSONDecodeError) as exc:
            failed.append((path, str(exc).splitlines()[0]))
            continue
        guide.steps.sort(key=lambda s: s.order)
        for i, step in enumerate(guide.steps, start=1):
            step.order = i
        for alias in internal_aliases.get(path.stem, []):
            if alias not in guide.aliases:
                guide.aliases.append(alias)
        out = args.maps / path.name
        out.write_text(guide.model_dump_json(indent=1))
        ok += 1

    print(f"{ok} guias curados em {args.maps}")
    for path, err in failed:
        print(f"FALHOU {path}: {err}", file=sys.stderr)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
