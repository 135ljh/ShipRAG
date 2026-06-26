from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
CHUNKS_PATH = BASE_DIR / "data" / "chapter5_chunks.jsonl"
DEFAULT_COLLECTION = "chapter5_rag_chunks"
DEFAULT_DIM = 384


def load_settings() -> tuple[str, str, int]:
    load_dotenv(ROOT / ".env")
    load_dotenv(BASE_DIR / ".env")
    url = os.getenv("CHAPTER5_QDRANT_URL", os.getenv("QDRANT_URL", "http://localhost:6333"))
    collection = os.getenv("CHAPTER5_QDRANT_COLLECTION", DEFAULT_COLLECTION)
    dim = int(os.getenv("CHAPTER5_EMBEDDING_DIM", str(DEFAULT_DIM)))
    return url, collection, dim


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def hash_embed(text: str, dim: int = DEFAULT_DIM) -> list[float]:
    vector = [0.0] * dim
    chars = [ch for ch in text if not ch.isspace()]
    tokens = chars[:]
    tokens.extend("".join(chars[index : index + 2]) for index in range(max(0, len(chars) - 1)))
    tokens.extend("".join(chars[index : index + 3]) for index in range(max(0, len(chars) - 2)))
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(item * item for item in vector)) or 1.0
    return [round(item / norm, 8) for item in vector]


class Chapter5Qdrant:
    def __init__(self) -> None:
        self.url, self.collection, self.dim = load_settings()
        self.storage_path = BASE_DIR / "qdrant_storage"
        self.mode = "http"
        self.client = QdrantClient(url=self.url)

    def use_local_storage(self) -> None:
        self.mode = "local"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(self.storage_path))

    def ensure_collection(self, recreate: bool = False) -> None:
        try:
            collections = self.client.get_collections().collections
        except Exception:
            self.use_local_storage()
            collections = self.client.get_collections().collections
        exists = any(item.name == self.collection for item in collections)
        if exists and recreate:
            self.client.delete_collection(self.collection)
            exists = False
        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )

    def ingest(self, recreate: bool = False) -> dict[str, Any]:
        chunks = read_jsonl(CHUNKS_PATH)
        self.ensure_collection(recreate=recreate)
        points = []
        for chunk in chunks:
            text = f"{chunk.get('chapter_hint', '')}\n{chunk.get('text', '')}"
            payload = {
                "chunk_id": chunk["id"],
                "source": chunk.get("source"),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "chapter_hint": chunk.get("chapter_hint", ""),
                "text": chunk.get("text", ""),
                "char_count": chunk.get("char_count", len(chunk.get("text", ""))),
            }
            points.append(
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"chapter5:{chunk['id']}")),
                    vector=hash_embed(text, self.dim),
                    payload=payload,
                )
            )
        if points:
            self.client.upsert(collection_name=self.collection, points=points)
        return {
            "collection": self.collection,
            "url": self.url,
            "mode": self.mode,
            "storage_path": str(self.storage_path) if self.mode == "local" else "",
            "points": len(points),
            "dim": self.dim,
        }

    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        self.ensure_collection(recreate=False)
        results = self.client.query_points(
            collection_name=self.collection,
            query=hash_embed(query, self.dim),
            limit=top_k,
            with_payload=True,
        ).points
        return [
            {
                "type": "document",
                "score": round(float(point.score), 6),
                "retrieval_source": "qdrant_vector",
                **(point.payload or {}),
            }
            for point in results
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest chapter 5 chunks into Qdrant.")
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()
    qdrant = Chapter5Qdrant()
    print(json.dumps(qdrant.ingest(recreate=args.recreate), ensure_ascii=False))


if __name__ == "__main__":
    main()
