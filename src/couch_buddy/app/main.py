"""Entry point: watcher + servidor + abertura do Chrome no 2º monitor."""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
from pathlib import Path

import uvicorn

from couch_buddy.app.companion import Companion
from couch_buddy.app.config import Config
from couch_buddy.app.server import create_app
from couch_buddy.brain.progress import ProgressStore
from couch_buddy.knowledge.library import GuideLibrary
from couch_buddy.state.watcher import SaveWatcher

log = logging.getLogger("couch_buddy")


def _load_guid_map(path: Path, blueprint_names: dict[str, dict]) -> dict[str, str]:
    """Nome de área por GUID: heurística dos saves < blueprint < manual."""
    raw = json.loads(path.read_text()) if path.exists() else {}
    guid_map = {guid: entry["name"] for guid, entry in raw.items()}
    for guid, entry in blueprint_names.items():
        if entry.get("type") == "BlueprintArea" and not raw.get(guid, {}).get("manual"):
            guid_map[guid] = entry["name"]
    return guid_map


def _latest_save(saves_dir: Path) -> Path | None:
    saves = list(saves_dir.glob("*.zks"))
    return max(saves, key=lambda p: p.stat().st_mtime) if saves else None


def _open_browser(port: int, position: str) -> None:
    cmd = [
        "google-chrome",
        f"--app=http://localhost:{port}",
        f"--window-position={position}",
        "--start-fullscreen",
    ]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        log.warning("google-chrome não encontrado; abra http://localhost:%s", port)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    config = Config()
    ap = argparse.ArgumentParser(description="Couch Buddy — Rogue Trader companion")
    ap.add_argument("--saves-dir", type=Path, default=config.saves_dir)
    ap.add_argument("--port", type=int, default=config.port)
    ap.add_argument("--no-open", action="store_true", help="não abrir o Chrome")
    args = ap.parse_args()

    names_path = config.data_dir / "blueprint_names.json"
    blueprint_names: dict[str, dict] = (
        json.loads(names_path.read_text()) if names_path.exists() else {}
    )
    companion = Companion(
        library=GuideLibrary(config.maps_dir),
        progress=ProgressStore(config.progress_dir),
        guid_map=_load_guid_map(config.guid_map_path, blueprint_names),
        blueprint_names=blueprint_names,
    )

    if latest := _latest_save(args.saves_dir):
        log.info("carregando último save: %s", latest.name)
        companion.on_save(latest)
    else:
        log.warning("nenhum save encontrado em %s", args.saves_dir)

    watcher = SaveWatcher(args.saves_dir, companion.on_save, config.debounce_s)
    watcher.start()
    log.info("observando %s", args.saves_dir)

    if not args.no_open:
        _open_browser(args.port, config.window_position)

    try:
        uvicorn.run(create_app(companion), host="127.0.0.1", port=args.port, log_level="warning")
    finally:
        watcher.stop()


if __name__ == "__main__":
    main()
