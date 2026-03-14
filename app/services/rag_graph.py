from __future__ import annotations

from typing import Any, TypedDict

from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.infrastructure.config.database.mongodb import connection as mongodb


class RagState(TypedDict):
    question: str
    session_id: str
    contexts: list[str]
    answer: str


async def load_context_from_mongo(state: RagState) -> RagState:
    if mongodb.db is None:
        state["contexts"] = []
        return state

    cursor = mongodb.db[settings.rag_knowledge_collection].find(
        {},
        {"_id": 0, "content": 1},
    ).limit(5)
    docs = await cursor.to_list(length=5)
    state["contexts"] = [d.get("content", "") for d in docs if d.get("content")]
    return state


async def generate_answer(state: RagState) -> RagState:
    llm = ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model, temperature=0)

    context_text = "\n\n".join(state["contexts"]) if state["contexts"] else "No internal knowledge yet."
    prompt = (
        "You are a helpful medical-management assistant.\n"
        "Use internal context when available. If no context, answer generally and be explicit.\n\n"
        f"Internal context:\n{context_text}\n\n"
        f"User question: {state['question']}"
    )

    response = await llm.ainvoke(prompt)
    state["answer"] = response.content if isinstance(response.content, str) else str(response.content)
    return state


async def persist_chat_history(state: RagState) -> RagState:
    if mongodb.db is None:
        return state

    await mongodb.db[settings.rag_chat_history_collection].insert_one(
        {
            "session_id": state["session_id"],
            "question": state["question"],
            "answer": state["answer"],
            "used_context_count": len(state["contexts"]),
        }
    )
    return state


graph_builder = StateGraph(RagState)
graph_builder.add_node("load_context_from_mongo", load_context_from_mongo)
graph_builder.add_node("generate_answer", generate_answer)
graph_builder.add_node("persist_chat_history", persist_chat_history)
graph_builder.add_edge(START, "load_context_from_mongo")
graph_builder.add_edge("load_context_from_mongo", "generate_answer")
graph_builder.add_edge("generate_answer", "persist_chat_history")
graph_builder.add_edge("persist_chat_history", END)
rag_graph = graph_builder.compile()


async def run_rag(question: str, session_id: str) -> dict[str, Any]:
    final_state = await rag_graph.ainvoke(
        {
            "question": question,
            "session_id": session_id,
            "contexts": [],
            "answer": "",
        }
    )
    return {
        "answer": final_state["answer"],
        "session_id": final_state["session_id"],
        "used_context_count": len(final_state["contexts"]),
    }
