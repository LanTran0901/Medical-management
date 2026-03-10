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
