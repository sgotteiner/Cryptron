"""One embedding model, one space (memory_design.md §2: recall is pgvector).

Gemini's embedding endpoint at 1536 dims to match the schema. Vectors are
L2-normalized (required whenever a non-default dimension is requested).
NEVER mix models: a second model is a second, incompatible similarity space.
"""
import math
import os

import httpx

MODEL = os.environ.get("EMBED_MODEL", "gemini-embedding-001")
DIM = 1536


async def embed(text: str, task: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """task: RETRIEVAL_DOCUMENT when indexing, RETRIEVAL_QUERY when searching."""
    key = os.environ["GEMINI_API_KEY"].strip()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:embedContent",
            params={"key": key},
            json={"content": {"parts": [{"text": text[:30000]}]},
                  "taskType": task, "outputDimensionality": DIM},
        )
        r.raise_for_status()
    vec = r.json()["embedding"]["values"]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
