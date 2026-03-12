from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    anthropic_api_key: str = ""  # via env ANTHROPIC_API_KEY
    data_dir: Path = Path("data/games")
    sonnet_model: str = "claude-sonnet-4-6"
    haiku_model: str = "claude-haiku-4-5"
    state_interval_seconds: float = 12.0
    state_confidence_threshold: float = 0.8
    capture_max_long_edge: int = 1568
    capture_jpeg_quality: int = 85
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_n_results: int = 5
