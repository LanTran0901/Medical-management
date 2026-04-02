from __future__ import annotations

import argparse

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.entities.medical_dictionary import DictionaryEntryType
from app.infrastructure.config.database.postgres.models.medical_dictionary_models import (
    DiseaseModel,
    DrugModel,
    VaccineModel,
)
from app.services.rag_support import build_search_document, embed_documents


MODEL_MAP = {
    DictionaryEntryType.DISEASE: DiseaseModel,
    DictionaryEntryType.DRUG: DrugModel,
    DictionaryEntryType.VACCINE: VaccineModel,
}


def reindex_vectors(*, batch_size: int) -> dict[str, int]:
    engine = sa.create_engine(settings.POSTGRES_SYNC_URL, future=True)
    counters = {
        DictionaryEntryType.DISEASE.value: 0,
        DictionaryEntryType.DRUG.value: 0,
        DictionaryEntryType.VACCINE.value: 0,
    }

    try:
        with Session(engine) as session:
            for entry_type, model in MODEL_MAP.items():
                rows = session.execute(sa.select(model).order_by(model.source_index.asc())).scalars().all()
                for start in range(0, len(rows), batch_size):
                    batch = rows[start:start + batch_size]
                    documents = [
                        build_search_document(
                            entry_type=entry_type,
                            title=row.title,
                            aliases=list(row.aliases or []),
                            summary=row.summary,
                            content=dict(row.content or {}),
                        )
                        for row in batch
                    ]
                    embeddings = embed_documents(documents)
                    for row, search_document, embedding in zip(batch, documents, embeddings, strict=True):
                        row.search_document = search_document
                        row.embedding = embedding
                        counters[entry_type.value] += 1
                session.commit()
        return counters
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill pgvector embeddings for medical dictionary tables")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Number of rows to embed per batch",
    )
    args = parser.parse_args()

    counters = reindex_vectors(batch_size=max(1, args.batch_size))
    print(
        "Reindexed rows -> "
        f"disease={counters['disease']}, drug={counters['drug']}, vaccine={counters['vaccine']}"
    )


if __name__ == "__main__":
    main()
