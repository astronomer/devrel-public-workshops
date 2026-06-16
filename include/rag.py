"""RAG retrieval over the context_units table for the AstroTrips agents.

retrieve_context is exposed as a native pydantic-ai tool (CONTEXT_TOOLSET) on the
prospect-interaction drafter agent. It does two-stage retrieval: vector search for
recall, then an LLM reranker for precision, which is the standard production RAG
shape and separates same-domain chunks far better than cosine similarity alone.
"""

from __future__ import annotations

import json
import logging

from pydantic_ai import FunctionToolset

log = logging.getLogger(__name__)

# Must match the model used to embed context_units in the context_engineering DAG;
# otherwise the query vector and the stored vectors live in different spaces.
_EMBEDDING_MODEL = "text-embedding-3-small"
# Reranking is a ranking task, not a reasoning task: a fast non-reasoning model is
# ~5x quicker than gpt-5-mini here and just as good at ordering candidates.
_RERANK_MODEL = "gpt-4.1-mini"


def _llm_rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    if len(candidates) <= 1:
        return candidates[:top_k]

    from include.aimlops.embeddings import openai_client

    listing = "\n\n".join(f"[{c['chunk_id']}] {c['title']}\n{c['body']}" for c in candidates)
    user = (
        f"Query:\n{query}\n\n"
        f"Candidates:\n{listing}\n\n"
        f"Rank the candidates by how well they help answer the query. Return JSON "
        f'{{"ranking": [chunk_id, ...]}} listing the {top_k} most relevant chunk_ids, '
        f"most relevant first. Use only the chunk_ids shown in brackets."
    )

    response = openai_client().chat.completions.create(
        model=_RERANK_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a precise retrieval reranker."},
            {"role": "user", "content": user},
        ],
    )
    order = json.loads(response.choices[0].message.content)["ranking"]

    by_id = {c["chunk_id"]: c for c in candidates}
    # dict.fromkeys dedups while preserving order: the model occasionally lists the
    # same chunk_id more than once, which would otherwise repeat a result.
    reranked = [by_id[cid] for cid in dict.fromkeys(order) if cid in by_id]
    if not reranked:
        log.warning(
            "reranker returned no valid chunk_ids (got %r); using vector order",
            order[:5],
        )
        return candidates[:top_k]
    seen = {c["chunk_id"] for c in reranked}
    reranked.extend(c for c in candidates if c["chunk_id"] not in seen)
    return reranked[:top_k]


def retrieve_context(query: str, limit: int = 10) -> list[dict]:
    """Search AstroTrips policy and product knowledge for material relevant to a query.

    Use this before answering a prospect to look up company reference material:
    trip offerings and prices, discount and promo-code rules, the pet policy
    (including pet-specific policies), and multi-leg trip and layover logistics.
    Returns the most relevant context units, most relevant first.

    Args:
        query: A natural-language question or topic to search for.
        limit: Maximum number of context units to return.

    Returns:
        A list of dicts, each with chunk_id, title, body, source_uri,
        and context_prefix, most relevant first.
    """
    from include.aimlops.embeddings import embed_texts
    from include.aimlops.persistence import get_duckdb_conn

    pool_size = max(limit * 4, 20)
    query_vector = embed_texts([query], model=_EMBEDDING_MODEL)[0]
    columns = ["chunk_id", "title", "body", "source_uri", "context_prefix"]

    conn = get_duckdb_conn()
    try:
        vector_rows = conn.execute(
            "SELECT chunk_id, title, body, source_uri, context_prefix "
            "FROM context_units "
            "WHERE archived = false AND embedding IS NOT NULL "
            "ORDER BY list_cosine_similarity(embedding, CAST(? AS FLOAT[])) DESC "
            "LIMIT ?",
            [query_vector, pool_size],
        ).fetchall()
    finally:
        conn.close()

    candidates = [dict(zip(columns, row)) for row in vector_rows]
    results = _llm_rerank(query, candidates, limit)

    vector_rank = {u["chunk_id"]: i for i, u in enumerate(candidates, start=1)}
    log.info(
        "retrieve_context query=%r: %d vector candidates, reranked (%s) to top %d",
        query, len(candidates), _RERANK_MODEL, len(results),
    )
    for position, unit in enumerate(results, start=1):
        log.info(
            "  #%d (vector #%d)  %s  %s",
            position, vector_rank[unit["chunk_id"]], unit["chunk_id"], unit["title"],
        )

    return results


CONTEXT_TOOLSET = FunctionToolset(tools=[retrieve_context])
