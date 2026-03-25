from __future__ import annotations

import uuid
from collections.abc import Iterable

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.medical_dictionary import DictionaryEntryType, MedicalDictionaryEntry
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
	) -> list[MedicalDictionaryEntry]:
		model = self._MODEL_MAP[entry_type]
		pattern = f"%{q}%"
		stmt = (
			sa.select(model)
			.where(
				sa.or_(
					model.title.ilike(pattern),
					model.summary.ilike(pattern),
					sa.cast(model.aliases, sa.Text).ilike(pattern),
				)
			)
			.order_by(model.title.asc())
		)
		rows = (await self._session.execute(stmt)).scalars().all()
		return [self._to_entity(row, entry_type) for row in rows]

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
