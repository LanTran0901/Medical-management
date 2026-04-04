from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import sqlalchemy as sa

from app.core.config import settings
from app.infrastructure.config.database.postgres.models.medical_dictionary_models import (
    DiseaseModel,
    DrugModel,
    VaccineModel,
)
from app.domain.entities.medical_dictionary import DictionaryEntryType
from app.services.rag_support import build_search_document, embed_documents


FILE_MAP: dict[str, tuple[type, str]] = {
    "disease": (DiseaseModel, "disease.json"),
    "drug": (DrugModel, "thuoc.json"),
    "vaccine": (VaccineModel, "vaccine.json"),
}

TITLE_KEYS: dict[str, tuple[str, ...]] = {
    "disease": ("disease_name",),
    "drug": ("drug_name", "generic_name", "brand_name"),
    "vaccine": ("vaccine_name",),
}

SUMMARY_KEYS: tuple[str, ...] = (
    "overview",
    "definition",
    "indications",
    "prevents_disease",
)

ALIAS_KEYS: tuple[str, ...] = (
    "generic_name",
    "brand_name",
)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_record(line: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for chunk in line.split(";"):
        part = chunk.strip()
        if not part or ":" not in part:
            continue
        key, value = part.split(":", 1)
        key = _normalize_text(key).lower()
        value = _normalize_text(value)
        if not value:
            continue
        if key in payload and payload[key] != value:
            payload[key] = f"{payload[key]} | {value}"
        else:
            payload[key] = value
    return payload


def _best_title(kind: str, payload: dict[str, str], fallback: str) -> str:
    for key in TITLE_KEYS[kind]:
        value = payload.get(key)
        if value and value.upper() != "N/A":
            return value
    for value in payload.values():
        if value and value.upper() != "N/A":
            return value
    return fallback


def _aliases(payload: dict[str, str], title: str) -> list[str]:
    aliases: list[str] = []
    for key in ALIAS_KEYS:
        value = payload.get(key)
        if not value or value.upper() == "N/A" or value == title:
            continue
        aliases.append(value)

    seen: set[str] = set()
    deduped: list[str] = []
    for alias in aliases:
        lowered = alias.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(alias)
    return deduped


def _summary(payload: dict[str, str]) -> str | None:
    for key in SUMMARY_KEYS:
        value = payload.get(key)
        if value and value.upper() != "N/A":
            return value
    return None


def _load_rows(
    data_dir: Path,
    kind: str,
    per_type: int | None,
    include_embeddings: bool,
) -> list[dict[str, Any]]:
    _, filename = FILE_MAP[kind]
    file_path = data_dir / filename
    if not file_path.exists():
        return []

    with file_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    rows: list[dict[str, Any]] = []
    search_documents: list[str] = []
    for idx, line in enumerate(raw, start=1):
        if per_type is not None and len(rows) >= per_type:
            break
        payload = _parse_record(str(line))
        if not payload:
            continue
        fallback = f"{kind}-{idx}"
        title = _best_title(kind, payload, fallback)
        entry_type = {
            "disease": DictionaryEntryType.DISEASE,
            "drug": DictionaryEntryType.DRUG,
            "vaccine": DictionaryEntryType.VACCINE,
        }[kind]
        search_document = build_search_document(
            entry_type=entry_type,
            title=title,
            aliases=_aliases(payload, title),
            summary=_summary(payload),
            content=payload,
        )
        rows.append(
            {
                "title": title,
                "aliases": _aliases(payload, title),
                "summary": _summary(payload),
                "content": payload,
                "search_document": search_document,
                "embedding": None,
                "source_file": filename,
            }
        )
        search_documents.append(search_document)

    if include_embeddings and search_documents:
        embeddings = embed_documents(search_documents)
        for row, embedding in zip(rows, embeddings, strict=True):
            row["embedding"] = embedding
    return rows


def seed_medical_dictionary(
    per_type: int | None,
    drop_legacy: bool,
    include_embeddings: bool,
    truncate_first: bool,
) -> dict[str, int]:
    engine = sa.create_engine(settings.POSTGRES_SYNC_URL, future=True)
    counters = {"disease": 0, "drug": 0, "vaccine": 0}
    data_dir = Path(settings.data_dir)

    try:
        DiseaseModel.__table__.create(bind=engine, checkfirst=True)
        DrugModel.__table__.create(bind=engine, checkfirst=True)
        VaccineModel.__table__.create(bind=engine, checkfirst=True)

        with engine.begin() as conn:
            if drop_legacy:
                conn.execute(sa.text("DROP TABLE IF EXISTS medical_dictionary_entries CASCADE"))
                conn.execute(sa.text("DROP TABLE IF EXISTS disease_dictionary_entries CASCADE"))
                conn.execute(sa.text("DROP TABLE IF EXISTS drug_dictionary_entries CASCADE"))
                conn.execute(sa.text("DROP TABLE IF EXISTS vaccine_dictionary_entries CASCADE"))
            if truncate_first:
                conn.execute(sa.text("TRUNCATE TABLE diseases, drugs, vaccines RESTART IDENTITY CASCADE"))

            for kind, (model, _) in FILE_MAP.items():
                rows = _load_rows(
                    data_dir=data_dir,
                    kind=kind,
                    per_type=per_type,
                    include_embeddings=include_embeddings,
                )
                if not rows:
                    continue
                conn.execute(sa.insert(model), rows)
                counters[kind] = len(rows)
        return counters
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed medical dictionary into separated PostgreSQL tables")
    parser.add_argument(
        "--per-type",
        type=int,
        default=3,
        help="Number of entries for each table (disease/drug/vaccine)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Seed all rows from each JSON file",
    )
    parser.add_argument(
        "--drop-legacy",
        action="store_true",
        help="Drop legacy medical_dictionary_entries table",
    )
    parser.add_argument(
        "--truncate-first",
        action="store_true",
        help="Delete existing rows in diseases, drugs, vaccines before seeding",
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Seed data without generating pgvector embeddings",
    )
    args = parser.parse_args()

    counters = seed_medical_dictionary(
        per_type=None if args.all else max(1, args.per_type),
        drop_legacy=args.drop_legacy,
        include_embeddings=not args.skip_embeddings,
        truncate_first=args.truncate_first,
    )
    print(
        "Seeded rows -> "
        f"disease={counters['disease']}, drug={counters['drug']}, vaccine={counters['vaccine']}"
    )


if __name__ == "__main__":
    main()
