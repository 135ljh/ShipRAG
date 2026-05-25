from __future__ import annotations

import argparse
import uuid

from qdrant_client.models import PointStruct
from tqdm import tqdm

from graph_rag.db.qdrant_client import ShipQdrantClient
from graph_rag.ingest.chunk_loader import load_chunks
from graph_rag.llm import OpenAIService


def batch(items: list[dict], size: int) -> list[list[dict]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed processed ShipRAG chunks and write them to Qdrant.")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    chunks = load_chunks()
    if args.limit:
        chunks = chunks[: args.limit]

    qdrant = ShipQdrantClient()
    qdrant.ensure_collection()
    llm = OpenAIService()

    for group in tqdm(batch(chunks, args.batch_size), desc="qdrant ingest"):
        vectors = llm.embed([item["text"] for item in group])
        points = []
        for item, vector in zip(group, vectors, strict=True):
            payload = {
                "chunk_id": item["id"],
                "source": item.get("source"),
                "page_start": item.get("page_start"),
                "page_end": item.get("page_end"),
                "chapter_hint": item.get("chapter_hint", ""),
                "text": item["text"],
                "char_count": item.get("char_count", len(item["text"])),
            }
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, item["id"]))
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))
        qdrant.client.upsert(collection_name=qdrant.collection, points=points)


if __name__ == "__main__":
    main()
