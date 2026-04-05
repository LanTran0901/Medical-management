from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.domain.entities.medical_dictionary import MedicalDictionaryEntry


class DictionarySearchItemResponse(BaseModel):
	id: str
	type: str
	title: str
	aliases: list[str]
	summary: str | None

	@classmethod
	def from_entity(cls, entry: MedicalDictionaryEntry) -> "DictionarySearchItemResponse":
		return cls(
			id=entry.id,
			type=entry.entry_type.value,
			title=entry.title,
			aliases=entry.aliases,
			summary=entry.summary,
		)


class DictionarySearchResponse(BaseModel):
	items: list[DictionarySearchItemResponse]
	total: int
	page: int
	limit: int
	has_next: bool


class DictionaryDetailResponse(BaseModel):
	id: str
	type: str
	title: str
	aliases: list[str]
	summary: str | None
	content: dict[str, Any]

	@classmethod
	from_entity(cls, entry: MedicalDictionaryEntry) -> "DictionaryDetailResponse":
		return cls(
			id=entry.id,
			type=entry.entry_type.value,
			title=entry.title,
			aliases=entry.aliases,
			summary=entry.summary,
			content=entry.content,
		)
