"""Tools exposed to the Researcher agent.

Kept local/deterministic (no external network calls) so the whole demo
runs offline against the bundled sample corpus in data/, and so unit
tests don't need real AWS or internet access to verify behavior. Swap
`search_documents` for a real Bedrock Knowledge Base / OpenSearch
retriever call to go to production.
"""
from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def search_documents(query: str, top_k: int = 3) -> str:
    """Naive keyword search over the local corpus."""
    query_terms = {t.lower() for t in query.split() if len(t) > 2}
    scored = []
    for path in sorted(DATA_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        score = sum(text.lower().count(term) for term in query_terms)
        if score:
            scored.append((score, path.name, text))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return "No matching documents found."
    hits = scored[:top_k]
    return "\n\n".join(f"[{name}]\n{text[:800]}" for _, name, text in hits)


TOOL_SPECS = [
    {
        "toolSpec": {
            "name": "search_documents",
            "description": "Search the local knowledge base for information relevant to a query.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                }
            },
        }
    }
]

TOOLS = {"search_documents": search_documents}
