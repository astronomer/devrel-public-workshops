import os
from datetime import datetime
from pathlib import Path

from airflow.configuration import AIRFLOW_HOME
from airflow.sdk import chain, dag, task
from pydantic import BaseModel, Field

from include.aimlops import chunking, context_units
from include.aimlops.assets import CONTEXT_UNITS_UPDATED, RAG_INDEX_UPDATED
from include.prompts import CONTEXT_STRUCTURE_SYSTEM_PROMPT

_SEED_DIR = Path(AIRFLOW_HOME) / "include" / "seed_context"
_DUCKDB_CONN_ID = os.getenv("MLOPS_TRACKING_CONN_ID", "duckdb_astrotrips")
_EMBEDDING_MODEL = "text-embedding-3-small"
_EMBED_BATCH = 64


class ChunkMeta(BaseModel):
    chunk_type: str = Field(description="informational / instructional / actionable")
    title: str = Field(description="short, specific label for the chunk")
    context_prefix: str = Field(description="1-2 sentences situating the chunk in its document")


@dag(
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["Bonus exercise 2"],
    doc_md=__doc__,
)
def context_engineering():

    @task
    def list_source_files() -> list[str]:
        return sorted(str(path) for path in _SEED_DIR.glob("*.md"))

    @task(map_index_template="{{ custom_map_index }}")
    def chunk_file(path: str) -> list[dict]:
        from airflow.sdk import get_current_context

        get_current_context()["custom_map_index"] = f"Chunk Title: {Path(path).name}"

        raw = Path(path).read_text(encoding="utf-8")
        frontmatter, chunks = chunking.chunk_markdown(raw)
        relpath = os.path.relpath(path, AIRFLOW_HOME)
        return [
            {
                "text": chunk.text,
                "heading_path": chunk.heading_path,
                "ordinal": chunk.ordinal,
                "source": frontmatter.get("source", relpath),
                "relpath": relpath,
                "doc_text": raw,
            }
            for chunk in chunks
        ]

    @task
    def flatten_chunks(chunked: list[list[dict]]) -> list[dict]:
        return [chunk for file_chunks in chunked for chunk in file_chunks]

    @task(map_index_template="{{ custom_map_index }}")
    def deterministic_meta(chunk: dict) -> dict:
        from airflow.sdk import get_current_context

        source_uri = context_units.build_source_uri(
            chunk["relpath"], chunk["heading_path"], chunk["ordinal"]
        )
        chunk_id = context_units.chunk_id_for(source_uri)

        context = get_current_context()
        context["custom_map_index"] = f"Chunk Title: {chunk['heading_path']}"

        return {
            **chunk,
            "source_uri": source_uri,
            "chunk_id": chunk_id,
            "tokens": chunking.count_tokens(chunk["text"]),
            "checksum": context_units.checksum_for(chunk["text"]),
            "source_type": "Human",
            "body": context_units.wrap_body(chunk_id, chunk["text"]),
            "version": 1,
            "archived": False,
        }

    @task.agent(
        llm_conn_id="pydanticai_default",
        output_type=ChunkMeta,
        system_prompt=CONTEXT_STRUCTURE_SYSTEM_PROMPT,
    )
    def ai_structure(chunk: dict) -> str:
        return (
            "Document:\n"
            f"{chunk['doc_text']}\n\n"
            "Chunk to annotate:\n"
            f"{chunk['text']}"
        )

    @task
    def merge_meta(deterministic: list[dict], structured: list) -> list[dict]:
        units = []
        for base, meta in zip(deterministic, structured):
            meta = meta if isinstance(meta, dict) else meta.model_dump()
            units.append(
                {
                    **base,
                    "chunk_type": meta["chunk_type"],
                    "title": meta["title"],
                    "context_prefix": meta["context_prefix"],
                }
            )
        return units

    @task
    def embed_units(units: list[dict]) -> list[dict]:
        from include.aimlops.embeddings import embed_texts

        inputs = [context_units.embedding_input(u["context_prefix"], u["text"]) for u in units]
        vectors = embed_texts(inputs, model=_EMBEDDING_MODEL, batch_size=_EMBED_BATCH)
        return [
            {**unit, "embedding": vector, "embedding_model": _EMBEDDING_MODEL}
            for unit, vector in zip(units, vectors)
        ]

    @task(outlets=[CONTEXT_UNITS_UPDATED, RAG_INDEX_UPDATED])
    def load_units(units: list[dict]) -> None:
        import duckdb
        from airflow.sdk import BaseHook

        db_path = BaseHook.get_connection(_DUCKDB_CONN_ID).host
        conn = duckdb.connect(db_path)
        try:
            by_file: dict[str, list[dict]] = {}
            for unit in units:
                by_file.setdefault(unit["relpath"], []).append(unit)
            for relpath, file_units in by_file.items():
                context_units.replace_units(conn, relpath, file_units)
        finally:
            conn.close()

    _files = list_source_files()
    _chunked = chunk_file.expand(path=_files)
    _flat = flatten_chunks(_chunked)
    _deterministic = deterministic_meta.expand(chunk=_flat)
    _structured = ai_structure.expand(chunk=_deterministic)
    _units = merge_meta(_deterministic, _structured)
    _embedded = embed_units(_units)
    _loaded = load_units(_embedded)
    chain(_units, _embedded, _loaded)


context_engineering()
