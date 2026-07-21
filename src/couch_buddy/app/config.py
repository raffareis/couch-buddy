from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_SAVES_DIR = Path(
    "/home/raffareis/Storage/SteamLibrary/steamapps/compatdata/2186680/pfx/drive_c"
    "/users/steamuser/AppData/LocalLow/Owlcat Games/Warhammer 40000 Rogue Trader"
    "/Saved Games"
)


@dataclass
class Config:
    saves_dir: Path = DEFAULT_SAVES_DIR
    data_dir: Path = PROJECT_ROOT / "data/games/rogue-trader"
    progress_dir: Path = PROJECT_ROOT / "data/progress"
    port: int = 8017
    # posição do Chrome no 2º ultrawide (xrandr: HDMI-1 em +1080+1308)
    window_position: str = "1080,1308"
    debounce_s: float = 2.0
    # fase 2 (visão); sem uso no MVP
    anthropic_api_key: str = ""  # via env ANTHROPIC_API_KEY
    sonnet_model: str = "claude-sonnet-5"
    haiku_model: str = "claude-haiku-4-5-20251001"
    state_interval_seconds: float = 12.0
    capture_max_long_edge: int = 1568
    capture_jpeg_quality: int = 85

    @property
    def maps_dir(self) -> Path:
        return self.data_dir / "maps"

    @property
    def guid_map_path(self) -> Path:
        return self.data_dir / "guid_map.json"
