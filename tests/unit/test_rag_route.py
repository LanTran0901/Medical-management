from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_rag_service
from app.routes.rag import router


def test_rag_chat_returns_sources(monkeypatch) -> None:
    async def fake_run_rag(*, question: str, session_id: str, rag_service):
        assert question == "HPV la gi?"
        assert session_id == "sess-1"
        assert rag_service == "fake-service"
        return {
            "answer": "Thong tin duoc tra ve tu kho noi bo.",
            "session_id": session_id,
            "used_context_count": 2,
            "sources": [
                {
                    "id": "src-1",
                    "entry_type": "vaccine",
                    "title": "Gardasil 9",
                    "score": 0.91,
                    "summary": "Vaccine phong HPV",
                }
            ],
        }

    monkeypatch.setattr("app.routes.rag.run_rag", fake_run_rag)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_rag_service] = lambda: "fake-service"

    with TestClient(app) as client:
        response = client.post(
            "/rag/chat",
            json={"question": "HPV la gi?", "session_id": "sess-1"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["used_context_count"] == 2
    assert payload["sources"][0]["title"] == "Gardasil 9"
