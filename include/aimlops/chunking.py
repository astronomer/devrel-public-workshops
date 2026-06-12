"""Deterministic Markdown chunking for the context-engineering pipeline.

Pure functions, no Airflow and no I/O, so they stay easy to read and reuse.
Strategy: split on Markdown headings first (each section is one coherent idea),
then recursively sub-split any section over the token budget on paragraph then
sentence boundaries, carrying a token-sized overlap between adjacent windows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken
import yaml

ENCODING_NAME = "cl100k_base"
TOKEN_BUDGET = 512
OVERLAP_TOKENS = 64

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass
class Chunk:
    text: str
    heading_path: list[str]
    ordinal: int


def count_tokens(text: str) -> int:
    return len(tiktoken.get_encoding(ENCODING_NAME).encode(text))


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw
    data = yaml.safe_load(match.group(1)) or {}
    return data, raw[match.end():]


def split_sections(body: str) -> list[tuple[list[str], str]]:
    sections: list[tuple[list[str], str]] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []

    def flush() -> None:
        text = "\n".join(buf).strip()
        if text:
            sections.append(([title for _, title in stack], text))

    for line in body.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            flush()
            buf.clear()
            level = len(match.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, match.group(2).strip()))
        else:
            buf.append(line)
    flush()
    return sections


def _split_units(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) > 1:
        return paragraphs
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _overlap_text(previous: str) -> str:
    enc = tiktoken.get_encoding(ENCODING_NAME)
    ids = enc.encode(previous)
    if len(ids) <= OVERLAP_TOKENS:
        return ""
    return enc.decode(ids[-OVERLAP_TOKENS:])


def _pack_with_overlap(text: str) -> list[str]:
    if count_tokens(text) <= TOKEN_BUDGET:
        return [text]
    units = _split_units(text)
    windows: list[str] = []
    current: list[str] = []
    for unit in units:
        candidate = current + [unit]
        if current and count_tokens("\n\n".join(candidate)) > TOKEN_BUDGET:
            joined = "\n\n".join(current)
            windows.append(joined)
            overlap = _overlap_text(joined)
            current = ([overlap] if overlap else []) + [unit]
        else:
            current = candidate
    if current:
        windows.append("\n\n".join(current))
    return windows


def chunk_markdown(raw: str) -> tuple[dict, list[Chunk]]:
    frontmatter, body = parse_frontmatter(raw)
    chunks: list[Chunk] = []
    for heading_path, text in split_sections(body):
        windows = _pack_with_overlap(text)
        for ordinal, window in enumerate(windows):
            chunks.append(
                Chunk(
                    text=window,
                    heading_path=heading_path,
                    ordinal=ordinal if len(windows) > 1 else 0,
                )
            )
    return frontmatter, chunks
