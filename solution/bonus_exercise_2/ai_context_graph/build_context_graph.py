from datetime import datetime

from airflow.sdk import chain, dag, task
from pydantic import BaseModel, Field

from include.aimlops.assets import (
    CONTEXT_UNITS_UPDATED,
    RAG_INDEX_UPDATED,
    TRACE_CREATED,
)
from include.prompts import CONTEXT_GRAPH_DISTILL_SYSTEM_PROMPT

_SOURCE = "context_graph"
_EMBEDDING_MODEL = "text-embedding-3-small"
_CONTEXT_PREFIX = "A learned precedent distilled from past AstroTrips sales decision traces."


class LearnedRule(BaseModel):
    title: str = Field(description="short, specific label for the rule")
    rule: str = Field(description="1-3 sentences of reusable guidance for the drafter")


@dag(
    start_date=datetime(2026, 1, 1),
    schedule=[TRACE_CREATED],
    catchup=False,
    tags=["Bonus exercise 2"],
    doc_md=__doc__,
)
def build_context_graph():

    @task
    def load_traces() -> list[dict]:
        from include.aimlops.persistence import load_records

        return load_records("decision_traces")

    @task.agent(
        llm_conn_id="pydanticai_default",
        output_type=LearnedRule,
        system_prompt=CONTEXT_GRAPH_DISTILL_SYSTEM_PROMPT,
    )
    def distill_rule(traces: list[dict]) -> str:
        return (
            "Distill one reusable rule from the most recent decision trace below.\n\n"
            f"{traces[-1]}"
        )

    @task(outlets=[CONTEXT_UNITS_UPDATED, RAG_INDEX_UPDATED])
    def publish_precedent(rule) -> None:
        import logging

        from include.aimlops import chunking, context_units
        from include.aimlops.embeddings import embed_texts
        from include.aimlops.persistence import get_duckdb_conn

        log = logging.getLogger("airflow.task")

        rule = rule if isinstance(rule, dict) else rule.model_dump()
        text = rule["rule"]
        title = rule["title"]

        source_uri = context_units.build_source_uri(_SOURCE, [title], 0)
        chunk_id = context_units.chunk_id_for(source_uri)
        embedding = embed_texts(
            [context_units.embedding_input(_CONTEXT_PREFIX, text)], model=_EMBEDDING_MODEL
        )[0]
        unit = {
            "chunk_id": chunk_id,
            "version": 1,
            "source_type": "ContextGraph",
            "chunk_type": "instructional",
            "tokens": chunking.count_tokens(text),
            "title": title,
            "checksum": context_units.checksum_for(text),
            "embedding_model": _EMBEDDING_MODEL,
            "body": context_units.wrap_body(chunk_id, text),
            "source_uri": source_uri,
            "context_prefix": _CONTEXT_PREFIX,
            "embedding": embedding,
            "archived": False,
        }

        with get_duckdb_conn() as conn:
            context_units.replace_units(conn, _SOURCE, [unit])

        log.info("Published learned precedent as context unit %s", chunk_id)
        log.info("  title: %s", title)
        log.info("  body:  %s", text)

    _traces = load_traces()
    _rule = distill_rule(_traces)
    _published = publish_precedent(_rule)
    chain(_traces, _rule, _published)


build_context_graph()
