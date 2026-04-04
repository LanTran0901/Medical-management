from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.medical_dictionary import (
	DictionaryEntryType,
	MedicalDictionaryEntry,
	MedicalDictionarySearchMatch,
)
from app.infrastructure.config.database.postgres.models.medical_dictionary_models import (
	DiseaseModel,
	DrugModel,
	VaccineModel,
)


class MedicalDictionaryRepository:
	_MODEL_MAP = {
		DictionaryEntryType.DISEASE: DiseaseModel,
		DictionaryEntryType.DRUG: DrugModel,
		DictionaryEntryType.VACCINE: VaccineModel,
	}

	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	def _to_entity(self, row: object, entry_type: DictionaryEntryType) -> MedicalDictionaryEntry:
		model = row
		return MedicalDictionaryEntry(
			id=str(model.id),
			entry_type=entry_type,
			title=model.title,
			aliases=list(model.aliases or []),
			summary=model.summary,
			content=dict(model.content or {}),
			source_file=model.source_file,
		)

	async def _search_one_type(
		self,
		*,
		entry_type: DictionaryEntryType,
		q: str,
		limit: int | None = None,
	) -> list[MedicalDictionaryEntry]:
		model = self._MODEL_MAP[entry_type]
		pattern = f"%{q}%"
		stmt = (
			sa.select(model)
			.where(
				sa.or_(
					model.title.ilike(pattern),
					model.summary.ilike(pattern),
					model.search_document.ilike(pattern),
					sa.cast(model.aliases, sa.Text).ilike(pattern),
				)
			)
			.order_by(model.title.asc())
		)
		if limit is not None:
			stmt = stmt.limit(limit)
		rows = (await self._session.execute(stmt)).scalars().all()
		return [self._to_entity(row, entry_type) for row in rows]

	async def _semantic_search_one_type(
		self,
		*,
		entry_type: DictionaryEntryType,
		query_embedding: list[float],
		limit: int,
	) -> list[MedicalDictionarySearchMatch]:
		model = self._MODEL_MAP[entry_type]
		distance = model.embedding.cosine_distance(query_embedding)
		stmt = (
			sa.select(model, distance.label("distance"))
			.where(model.embedding.is_not(None))
			.order_by(distance.asc(), model.title.asc())
			.limit(limit)
		)
		rows = (await self._session.execute(stmt)).all()
		matches: list[MedicalDictionarySearchMatch] = []
		for row in rows:
			entry = self._to_entity(row[0], entry_type)
			distance_value = float(row.distance if row.distance is not None else 1.0)
			score = max(0.0, 1.0 - distance_value)
			matches.append(MedicalDictionarySearchMatch(entry=entry, score=score))
		return matches

	async def semantic_search(
		self,
		*,
		query_embedding: list[float],
		top_k: int,
		per_type_limit: int,
	) -> list[MedicalDictionarySearchMatch]:
		bucket: list[MedicalDictionarySearchMatch] = []
		for current_type in (
			DictionaryEntryType.DISEASE,
			DictionaryEntryType.DRUG,
			DictionaryEntryType.VACCINE,
		):
			bucket.extend(
				await self._semantic_search_one_type(
					entry_type=current_type,
					query_embedding=query_embedding,
					limit=per_type_limit,
				)
			)

		bucket.sort(key=lambda item: item.score, reverse=True)
		return bucket[:top_k]

	async def keyword_search_for_rag(
		self,
		*,
		q: str,
		top_k: int,
		per_type_limit: int,
	) -> list[MedicalDictionarySearchMatch]:
		bucket: list[MedicalDictionarySearchMatch] = []
		for current_type in (
			DictionaryEntryType.DISEASE,
			DictionaryEntryType.DRUG,
			DictionaryEntryType.VACCINE,
		):
			items = await self._search_one_type(
				entry_type=current_type,
				q=q,
				limit=per_type_limit,
			)
			for rank, entry in enumerate(items):
				score = max(0.05, 0.5 - (rank * 0.05))
				bucket.append(MedicalDictionarySearchMatch(entry=entry, score=score))

		bucket.sort(key=lambda item: item.score, reverse=True)
		return bucket[:top_k]

	async def search(
		self,
		*,
		q: str,
		entry_type: DictionaryEntryType | None,
		page: int,
		limit: int,
	) -> tuple[list[MedicalDictionaryEntry], int]:
		query_text = q.strip()
		if entry_type is not None:
			items = await self._search_one_type(entry_type=entry_type, q=query_text)
		else:
			bucket: list[MedicalDictionaryEntry] = []
			for current_type in (
				DictionaryEntryType.DISEASE,
				DictionaryEntryType.DRUG,
				DictionaryEntryType.VACCINE,
			):
				bucket.extend(await self._search_one_type(entry_type=current_type, q=query_text))
			items = sorted(bucket, key=lambda x: (x.title.lower(), x.entry_type.value))

		total = len(items)
		start = (page - 1) * limit
		end = start + limit
		return items[start:end], total

	async def get_by_id(
		self,
		*,
		entry_type: DictionaryEntryType,
		item_id: str,
	) -> MedicalDictionaryEntry | None:
		model = self._MODEL_MAP[entry_type]
		try:
			parsed_id = uuid.UUID(item_id)
		except ValueError:
			return None

		stmt = sa.select(model).where(model.id == parsed_id)
		row = (await self._session.execute(stmt)).scalar_one_or_none()
		if row is None:
			return None
		return self._to_entity(row, entry_type)
