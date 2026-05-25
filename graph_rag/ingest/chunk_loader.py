from __future__ import annotations

import json
from pathlib import Path

from graph_rag.config import settings


def load_chunks(path: Path | None = None) -> list[dict]:
    path = path or settings.chunks_path
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

