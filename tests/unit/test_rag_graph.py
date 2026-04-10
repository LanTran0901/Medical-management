from __future__ import annotations

from app.services.rag_graph import _format_recent_history


def test_format_recent_history_empty() -> None:
    text = _format_recent_history([])
    assert "Khong co lich su hoi thoai" in text


def test_format_recent_history_includes_turns() -> None:
    text = _format_recent_history(
        [
            {"question": "HPV la gi?", "answer": "HPV la virus."},
            {"question": "Co nguy hiem khong?", "answer": "Can tiem vaccine theo tu van."},
        ]
    )

    assert "Luot 1 - Nguoi dung: HPV la gi?" in text
    assert "Luot 1 - Tro ly: HPV la virus." in text
    assert "Luot 2 - Nguoi dung: Co nguy hiem khong?" in text
