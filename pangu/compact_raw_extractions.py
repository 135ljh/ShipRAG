from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "pangu" / "outputs" / "raw_extractions.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compact raw Pangu extraction rows by chunk id.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.raw.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_chunk: dict[str, dict] = {}
    for row in rows:
        chunk_id = row["source_chunk"]
        current = by_chunk.get(chunk_id)
        if current is None:
            by_chunk[chunk_id] = row
            continue
        if current.get("error") and not row.get("error"):
            by_chunk[chunk_id] = row
        elif bool(current.get("error")) == bool(row.get("error")):
            by_chunk[chunk_id] = row

    compacted = sorted(by_chunk.values(), key=lambda r: (int(r.get("source_page") or 0), r["source_chunk"]))
    args.raw.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in compacted),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "before": len(rows),
                "after": len(compacted),
                "success": sum(1 for row in compacted if not row.get("error")),
                "errors": sum(1 for row in compacted if row.get("error")),
                "triples": sum(len(row.get("triples", [])) for row in compacted),
                "entities": sum(len(row.get("entities", [])) for row in compacted),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
