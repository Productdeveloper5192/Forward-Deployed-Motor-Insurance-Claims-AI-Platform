"""Lightweight sparse retrieval over the policy handbook.

No vector DB dependency for the MVP: chunks are split by markdown section and
ranked by keyword overlap with the query. Good enough for a handbook of this
size; swap in an embeddings-based store without changing the node that calls
`retrieve()` if the corpus grows.
"""

import re
from dataclasses import dataclass
from pathlib import Path

HANDBOOK_PATH = Path(__file__).resolve().parent.parent / "policy_data" / "policy_handbook.md"

_STOPWORDS = {
    "the", "a", "an", "is", "of", "to", "and", "or", "in", "for", "on", "at",
    "this", "that", "with", "as", "be", "are", "it", "was", "will", "if",
}


@dataclass
class Chunk:
    title: str
    text: str


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _load_chunks() -> list[Chunk]:
    raw = HANDBOOK_PATH.read_text(encoding="utf-8")
    sections = re.split(r"\n(?=## )", raw.strip())
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        title_match = re.match(r"##\s*(.+)", section)
        title = title_match.group(1).strip() if title_match else "Overview"
        chunks.append(Chunk(title=title, text=section))
    return chunks


_CHUNKS = _load_chunks()


def retrieve(query: str, top_k: int = 4) -> list[Chunk]:
    query_tokens = _tokenize(query)
    scored = []
    for chunk in _CHUNKS:
        overlap = len(query_tokens & _tokenize(chunk.text))
        if overlap:
            scored.append((overlap, chunk))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if not scored:
        return _CHUNKS[:top_k]
    return [chunk for _, chunk in scored[:top_k]]
