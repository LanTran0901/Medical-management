from __future__ import annotations

from app.domain.entities.medical_dictionary import DictionaryEntryType, MedicalDictionaryEntry
from app.infrastructure.repositories.medical_dictionary_repository import MedicalDictionaryRepository


class MedicalDictionaryService:
	def __init__(self, repository: MedicalDictionaryRepository) -> None:
		self._repository = repository

	async def search(
		self,
		*,
		q: str,
		entry_type: DictionaryEntryType | None,
		page: int,
		limit: int,
	) -> tuple[list[MedicalDictionaryEntry], int]:
		return await self._repository.search(
			q=q,
			entry_type=entry_type,
			page=page,
			limit=limit,
		)

	async def get_detail(
		self,
		*,
		entry_type: DictionaryEntryType,
		item_id: str,
	) -> MedicalDictionaryEntry:
		entry = await self._repository.get_by_id(entry_type=entry_type, item_id=item_id)
		if entry is None:
			raise ValueError("Dictionary entry not found")
		return entry
