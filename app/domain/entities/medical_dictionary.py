from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DictionaryEntryType(StrEnum):
	DISEASE = "disease"
	DRUG = "drug"
	VACCINE = "vaccine"


@dataclass(frozen=True, slots=True)
class MedicalDictionaryEntry:
	id: str
	entry_type: DictionaryEntryType
	title: str
	aliases: list[str]
	summary: str | None
	content: dict[str, str]
	source_file: str | None = None


@dataclass(frozen=True, slots=True)
class MedicalDictionarySearchMatch:
	entry: MedicalDictionaryEntry
	score: float
