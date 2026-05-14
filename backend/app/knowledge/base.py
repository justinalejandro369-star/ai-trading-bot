"""
backend/app/knowledge/base.py
Knowledge base loader for trading education and signal context.
Provides curated trading knowledge without requiring embeddings or a vector DB.

RELEVANT FILES: app/analysis/explainer.py, app/chat/context_builder.py, app/knowledge/docs/
"""
import logging
import os
from pathlib import Path

__all__ = ["get_relevant_context", "load_knowledge_base"]

log = logging.getLogger(__name__)

# Each section is a (header, content) tuple parsed from markdown files
_sections: list[tuple[str, str]] = []

# Directory containing the markdown knowledge files
_DOCS_DIR = Path(__file__).parent / "docs"


def load_knowledge_base() -> None:
    """
    Load all markdown files from the docs/ directory and parse them into sections.

    Sections are split by ## headers. Each section becomes a searchable unit.
    Called once at startup — the knowledge base is static and lives in memory.
    """
    global _sections
    _sections = []

    if not _DOCS_DIR.exists():
        log.warning("Knowledge base docs directory not found: %s", _DOCS_DIR)
        return

    for md_file in sorted(_DOCS_DIR.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            _parse_markdown(text, source=md_file.name)
        except Exception as exc:
            log.warning("Failed to load knowledge file %s: %s", md_file.name, exc)

    log.info("Knowledge base loaded: %d sections from %s", len(_sections), _DOCS_DIR)


def _parse_markdown(text: str, source: str = "") -> None:
    """
    Parse markdown text into sections split by ## headers.

    Each section gets stored as (header_lower, content) where header_lower
    is the lowercase header text for keyword matching.
    """
    current_header = source  # Use filename as default header for content before first ##
    current_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("## "):
            # Save previous section if it has content
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    _sections.append((current_header.lower(), content))
            current_header = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            _sections.append((current_header.lower(), content))


def get_relevant_context(keywords: list[str], max_chars: int = 3000) -> str:
    """
    Select knowledge sections relevant to the given keywords.

    Pure function — no DB, no external calls. Matches keywords against
    section headers using simple substring matching.

    Args:
        keywords: List of lowercase keyword strings to match against section headers.
        max_chars: Maximum total characters to return (prevents exceeding LLM context).

    Returns:
        Concatenated relevant sections as a string, or "" if no matches.
    """
    # Load on first call if not yet loaded (lazy init)
    if not _sections:
        load_knowledge_base()

    if not keywords or not _sections:
        return ""

    # Normalize keywords to lowercase for matching
    normalized = [k.lower().strip() for k in keywords if k.strip()]
    if not normalized:
        return ""

    # Score each section by how many keywords match its header
    scored: list[tuple[int, str]] = []
    for header, content in _sections:
        score = sum(1 for kw in normalized if kw in header)
        if score > 0:
            scored.append((score, content))

    # Sort by score descending — most relevant sections first
    scored.sort(key=lambda x: x[0], reverse=True)

    # Concatenate sections up to max_chars
    result_parts: list[str] = []
    total = 0
    for _score, content in scored:
        if total + len(content) > max_chars:
            # Include partial content if we have room
            remaining = max_chars - total
            if remaining > 100:  # Only include if we can fit something meaningful
                result_parts.append(content[:remaining] + "...")
            break
        result_parts.append(content)
        total += len(content)

    return "\n\n".join(result_parts)
