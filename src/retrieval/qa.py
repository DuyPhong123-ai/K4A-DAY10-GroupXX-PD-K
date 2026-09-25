from __future__ import annotations

from dataclasses import dataclass
import re

from core.config import Settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult


UNKNOWN_ANSWER = "I don't know from the indexed corpus."


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata
    if "author" in lowered or "who wrote" in lowered:
        return str(metadata.get("authors_joined") or UNKNOWN_ANSWER)
    if "when was" in lowered or "publication date" in lowered or "published" in lowered:
        return str(metadata.get("published") or UNKNOWN_ANSWER)
    if "categor" in lowered or "research field" in lowered or "subject" in lowered:
        return str(metadata.get("categories_joined") or UNKNOWN_ANSWER)
    summary = str(metadata.get("summary") or "")
    return first_sentence(summary) if summary else UNKNOWN_ANSWER


def _find_exact_document(question: str, index: LocalEmbeddingIndex) -> dict | None:
    quoted_values = re.findall(r"['\"]([^'\"]+)['\"]", question)
    for value in quoted_values:
        match = index.lookup(value)
        if match:
            return match

    doi_match = re.search(r"\b10\.\d{4,9}/[^\s'\"<>]+", question, flags=re.IGNORECASE)
    if doi_match:
        return index.lookup(doi_match.group(0).rstrip(".,;:!?)]}"))
    return None


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    question = question.strip()
    if not question:
        return AnswerResult(
            question="",
            answer=UNKNOWN_ANSWER,
            retrieved_doc_ids=[],
            retrieved_contexts=[],
            retrieved_titles=[],
        )

    exact = _find_exact_document(question, index)
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        deduped = [exact_result] + [item for item in retrieved if item.paper_id != exact_result.paper_id]
        retrieved = deduped[: (top_k or settings.top_k)]
    if not retrieved:
        answer = UNKNOWN_ANSWER
    else:
        answer = _extract_answer(question, retrieved[0])
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
    )
