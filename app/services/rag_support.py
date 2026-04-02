from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

from app.core.config import settings
from app.domain.entities.medical_dictionary import DictionaryEntryType, MedicalDictionaryEntry

_DEFAULT_FIELDS: dict[DictionaryEntryType, tuple[str, ...]] = {
    DictionaryEntryType.DISEASE: (
        "definition",
        "overview",
        "causes",
        "risk_factors",
        "symptoms",
        "red_flags",
        "diagnosis",
        "treatment",
        "home_care",
        "prevention",
    ),
    DictionaryEntryType.DRUG: (
        "generic_name",
        "brand_name",
        "active_ingredients",
        "indications",
        "contraindications",
        "dosage_adult",
        "dosage_children",
        "administration",
        "side_effects_common",
        "side_effects_serious",
    ),
    DictionaryEntryType.VACCINE: (
        "prevents_disease",
        "manufacturer",
        "country_of_origin",
        "indications",
        "eligible_population",
        "schedule",
        "booster_schedule",
        "route",
        "dose_volume",
    ),
}


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip()


def tokenize_query(query: str) -> set[str]:
    normalized = normalize_text(query).lower()
    return {token for token in re.findall(r"\w+", normalized) if len(token) >= 2}


def build_search_document(
    *,
    entry_type: DictionaryEntryType,
    title: str,
    aliases: list[str],
    summary: str | None,
    content: dict[str, str],
) -> str:
    parts = [f"Loai: {entry_type.value}", f"Tieu de: {normalize_text(title)}"]
    if aliases:
        parts.append("Alias: " + ", ".join(normalize_text(alias) for alias in aliases if normalize_text(alias)))
    if summary:
        parts.append(f"Tom tat: {normalize_text(summary)}")

    for key, value in content.items():
        clean_value = normalize_text(str(value))
        if not clean_value or clean_value.upper() == "N/A":
            continue
        parts.append(f"{key}: {clean_value}")
    return "\n".join(parts)


def format_entry_context(
    entry: MedicalDictionaryEntry,
    *,
    question: str,
    score: float,
    max_fields: int = 8,
    max_value_length: int = 360,
) -> str:
    tokens = tokenize_query(question)
    selected_items: list[tuple[str, str]] = []
    content_items = list(entry.content.items())

    def _field_score(item: tuple[str, str]) -> tuple[int, int]:
        key, value = item
        haystack = f"{key} {value}".lower()
        match_count = sum(1 for token in tokens if token in haystack)
        default_priority = _DEFAULT_FIELDS.get(entry.entry_type, ()).index(key) if key in _DEFAULT_FIELDS.get(entry.entry_type, ()) else 99
        return (match_count, -default_priority)

    ranked_items = sorted(content_items, key=_field_score, reverse=True)

    for key, value in ranked_items:
        cleaned = normalize_text(str(value))
        if not cleaned or cleaned.upper() == "N/A":
            continue
        selected_items.append((key, cleaned[:max_value_length]))
        if len(selected_items) >= max_fields:
            break

    if not selected_items:
        for key in _DEFAULT_FIELDS.get(entry.entry_type, ()):
            value = entry.content.get(key)
            cleaned = normalize_text(str(value)) if value is not None else ""
            if not cleaned or cleaned.upper() == "N/A":
                continue
            selected_items.append((key, cleaned[:max_value_length]))
            if len(selected_items) >= max_fields:
                break

    lines = [
        f"Nguon: {entry.entry_type.value}",
        f"Tieu de: {entry.title}",
        f"Diem phu hop: {score:.4f}",
    ]
    if entry.aliases:
        lines.append("Alias: " + ", ".join(entry.aliases))
    if entry.summary:
        lines.append(f"Tom tat: {normalize_text(entry.summary)[:max_value_length]}")
    lines.extend(f"{key}: {value}" for key, value in selected_items)
    return "\n".join(lines)


def _supports_e5_prefix(model_name: str) -> bool:
    lowered = model_name.lower()
    return "e5" in lowered


def _ensure_multilingual_e5_registered() -> None:
    TextEmbedding.add_custom_model(
        model="intfloat/multilingual-e5-small",
        pooling=PoolingType.MEAN,
        normalization=True,
        sources=ModelSource(hf="intfloat/multilingual-e5-small"),
        dim=384,
        model_file="onnx/model.onnx",
    )


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    model_name = settings.rag_embedding_model
    try:
        return TextEmbedding(model_name=model_name)
    except ValueError:
        if model_name == "intfloat/multilingual-e5-small":
            _ensure_multilingual_e5_registered()
            return TextEmbedding(model_name=model_name)
        raise


def embed_documents(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    payloads = [
        f"passage: {normalize_text(text)}" if _supports_e5_prefix(settings.rag_embedding_model) else normalize_text(text)
        for text in texts
    ]
    return [embedding.tolist() for embedding in model.embed(payloads)]


def embed_query(text: str) -> list[float]:
    model = get_embedding_model()
    payload = normalize_text(text)
    if _supports_e5_prefix(settings.rag_embedding_model):
        payload = f"query: {payload}"
    return next(model.embed([payload])).tolist()
