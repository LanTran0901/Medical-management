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

## Cau hinh moi truong

File `.env`:

```env
APP_NAME="Medical Management API"
MONGODB_URI="mongodb://localhost:27017"
MONGODB_DB_NAME="medical_management"
```

## Chay ung dung

```powershell
pipenv run start
```

Hoac:

```powershell
pipenv run uvicorn app.main:app --reload
```

## Chay bang Docker

```powershell
docker compose up -d --build
```

Stop:

```powershell
docker compose down
```

Xoa ca volume MongoDB:

```powershell
docker compose down -v
```

## Kiem tra

- API root: `http://127.0.0.1:8080/`
- Health check: `http://127.0.0.1:8080/health`
- Swagger UI: `http://127.0.0.1:8080/docs`
