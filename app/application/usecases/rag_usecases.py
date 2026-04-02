from __future__ import annotations

from dataclasses import dataclass

import asyncio

from app.core.config import settings
from app.domain.entities.medical_dictionary import MedicalDictionaryEntry
from app.infrastructure.repositories.medical_dictionary_repository import MedicalDictionaryRepository
from app.services.rag_support import embed_query, format_entry_context


@dataclass(frozen=True, slots=True)
class RagRetrievedSource:
    id: str
    entry_type: str
    title: str
    score: float
    summary: str | None
    context_text: str


class MedicalRagService:
    def __init__(self, repository: MedicalDictionaryRepository) -> None:
        self._repository = repository

    async def retrieve_sources(self, *, question: str) -> list[RagRetrievedSource]:
        matches = []
        try:
            query_vector = await asyncio.to_thread(embed_query, question)
            matches = await self._repository.semantic_search(
                query_embedding=query_vector,
                top_k=settings.rag_top_k,
                per_type_limit=settings.rag_per_type_limit,
            )
        except Exception:
            matches = []

        if not matches:
            matches = await self._repository.keyword_search_for_rag(
                q=question.strip(),
                top_k=settings.rag_top_k,
                per_type_limit=settings.rag_per_type_limit,
            )

        return [
            self._to_source(entry=match.entry, score=match.score, question=question)
            for match in matches
        ]

    def _to_source(
        self,
        *,
        entry: MedicalDictionaryEntry,
        score: float,
        question: str,
    ) -> RagRetrievedSource:
        return RagRetrievedSource(
            id=entry.id,
            entry_type=entry.entry_type.value,
            title=entry.title,
            score=score,
            summary=entry.summary,
            context_text=format_entry_context(entry, question=question, score=score),
        )
