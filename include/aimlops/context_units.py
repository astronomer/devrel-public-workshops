"""Deterministic metacontext and DuckDB persistence for context units."""

from __future__ import annotations

import hashlib
import re
import uuid

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")

_INSERT_COLUMNS = [
    "chunk_id", "version", "source_type", "chunk_type", "tokens", "title",
    "checksum", "embedding_model", "body", "source_uri", "context_prefix",
    "embedding", "archived",
]


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")


def build_source_uri(relpath: str, heading_path: list[str], ordinal: int) -> str:
    anchor = slugify(heading_path[-1]) if heading_path else "root"
    return f"{relpath}#{anchor}-{ordinal}"


def chunk_id_for(source_uri: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, source_uri))


def checksum_for(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wrap_body(chunk_id: str, text: str) -> str:
    return f'<chunk id="{chunk_id}">\n{text}\n</chunk>'


def embedding_input(context_prefix: str, text: str) -> str:
    return f"{context_prefix}\n\n{text}"


def replace_units(conn, relpath: str, units: list[dict]) -> None:
    conn.execute("DELETE FROM context_units WHERE source_uri LIKE ?", [f"{relpath}#%"])
    placeholders = ", ".join(["?"] * len(_INSERT_COLUMNS))
    columns = ", ".join(_INSERT_COLUMNS)
    for unit in units:
        conn.execute(
            f"INSERT INTO context_units ({columns}) VALUES ({placeholders})",
            [unit[column] for column in _INSERT_COLUMNS],
        )
