# FastAPI Pipenv Test

Du an FastAPI toi gian de test Python voi `pipenv`.

## Yeu cau

- Python 3.12
- `pipenv` da duoc cai san
- MongoDB dang chay local hoac remote

## Cai dat

```powershell
pipenv install
```

## Cau hinh moi truong (MongoDB Atlas)

Tao file `.env` tu mau:

```powershell
copy .env.example .env
```

Noi dung mau trong `.env.example`:

```env
APP_NAME="Medical Management API"
MONGODB_URI="mongodb+srv://<username>:<password>@<cluster-url>/<db-name>?retryWrites=true&w=majority&appName=<app-name>"
# Optional: set this only if you want to override db name parsed from MONGODB_URI
MONGODB_DB_NAME=""
GROQ_API_KEY="gsk_xxx"
GROQ_MODEL="llama-3.1-8b-instant"
RAG_KNOWLEDGE_COLLECTION="rag_knowledge"
RAG_CHAT_HISTORY_COLLECTION="rag_chat_history"
```

Luu y:
- Lay connection string trong Atlas: `Database > Connect > Drivers`.
- Neu password co ky tu dac biet (`@`, `#`, `%`...), can URL-encode truoc khi gan vao URI.

## Chay ung dung

```powershell
pipenv run start
```

Hoac:

```powershell
pipenv run uvicorn app.main:app --reload
```

## Chay bang Docker (chi app, ket noi Atlas)

```powershell
docker compose up -d --build
```

Stop:

```powershell
docker compose down
```

## Kiem tra

- API root: `http://127.0.0.1:8080/`
- Health check: `http://127.0.0.1:8080/health`
- Swagger UI: `http://127.0.0.1:8080/docs`

## Test luong RAG

Endpoint:

`POST /rag/chat`

Body:

```json
{
  "session_id": "demo-session-1",
  "question": "Quy trinh tiep nhan benh nhan ngoai tru?"
}
```

Giai doan hien tai:
- Chua bat buoc co knowledge.
- Neu collection `rag_knowledge` trong Mongo trong, he thong van tra loi bang LLM.
- Moi cau hoi/tra loi se duoc luu vao `rag_chat_history`.
