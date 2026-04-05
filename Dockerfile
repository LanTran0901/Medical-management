FROM python:3.12-slim

ARG INSTALL_TEST_DEPS=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock ./

# Cài dependencies từ lock. Thêm pin pgvector: Alembic import model có `from pgvector.sqlalchemy import VECTOR`;
# nếu thiếu wheel (một số môi trường build) thì migration sẽ lỗi ModuleNotFoundError.
RUN pipenv install --system --deploy --ignore-pipfile \
    && pip install --no-cache-dir "pgvector==0.4.2"

RUN if [ "$INSTALL_TEST_DEPS" = "1" ]; then \
      pip install --no-cache-dir pytest pytest-asyncio pytest-cov; \
    fi

COPY . .

EXPOSE 7543

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7543"]
