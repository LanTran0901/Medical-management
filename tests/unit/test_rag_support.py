from __future__ import annotations

from app.domain.entities.medical_dictionary import DictionaryEntryType, MedicalDictionaryEntry
from app.services.rag_support import build_search_document, format_entry_context


def test_build_search_document_includes_core_fields() -> None:
    document = build_search_document(
        entry_type=DictionaryEntryType.DRUG,
        title="Paracetamol 500mg",
        aliases=["Acetaminophen"],
        summary="Thuoc giam dau, ha sot",
        content={
            "indications": "Ha sot, giam dau nhe den vua",
            "dosage_adult": "500mg moi 4-6 gio khi can",
        },
    )

    assert "Loai: drug" in document
    assert "Tieu de: Paracetamol 500mg" in document
    assert "Alias: Acetaminophen" in document
    assert "indications: Ha sot, giam dau nhe den vua" in document


def test_format_entry_context_prioritizes_matching_fields() -> None:
    entry = MedicalDictionaryEntry(
        id="demo-id",
        entry_type=DictionaryEntryType.VACCINE,
        title="Gardasil 9",
        aliases=[],
        summary="Vaccine phong HPV",
        content={
            "prevents_disease": "HPV",
            "schedule": "2 hoac 3 mui tuy theo do tuoi",
            "route": "Tiem bap",
        },
        source_file="vaccine.json",
    )

    context = format_entry_context(
        entry,
        question="Lich tiem Gardasil 9 nhu the nao?",
        score=0.92,
    )

    assert "Tieu de: Gardasil 9" in context
    assert "schedule: 2 hoac 3 mui tuy theo do tuoi" in context
