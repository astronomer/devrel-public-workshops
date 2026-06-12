"""Thin wrappers around the OpenAI API for the context pipeline (embeddings, rerank)."""

from __future__ import annotations

import os


def _resolve_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    from airflow.sdk import BaseHook

    conn = BaseHook.get_connection("pydanticai_default")
    return conn.password or (conn.extra_dejson or {}).get("api_key")


def openai_client():
    from openai import OpenAI

    return OpenAI(api_key=_resolve_api_key())


def embed_texts(texts: list[str], model: str, batch_size: int = 64) -> list[list[float]]:
    client = openai_client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        response = client.embeddings.create(model=model, input=texts[start:start + batch_size])
        vectors.extend(item.embedding for item in response.data)
    return vectors
