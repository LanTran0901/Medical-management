#!/usr/bin/env python3
"""Một lần chạy: Alembic upgrade + toàn bộ pytest (unit + integration).

Dùng trên host khi đã có Postgres (local hoặc đã `docker compose up postgres`).
Trong Docker test, compose đã gọi tương đương trong `docker-compose.test.yml`.

Usage:
  python scripts/run_all_tests.py           # mặc định: migrate + pytest tests/
  python scripts/run_all_tests.py --cov     # bật coverage theo pytest.ini
  python scripts/run_all_tests.py -- tests/integration/ -k smoke -x
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Alembic upgrade + pytest full suite")
    parser.add_argument(
        "--cov",
        action="store_true",
        help="Bật coverage (bỏ --no-cov; dùng addopts trong pytest.ini)",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Thêm sau -- để truyền cho pytest",
    )
    args = parser.parse_args()
    if args.pytest_args and args.pytest_args[0] == "--":
        args.pytest_args = args.pytest_args[1:]

    root = Path(__file__).resolve().parent.parent
    app_dir = root / "app"
    os.environ.setdefault("SKIP_MONGO_LIFESPAN", "1")
    os.environ.setdefault("HOMEDMEDAI_INTEGRATION", "1")

    r = subprocess.run(
        [sys.executable, "-m", "alembic", "--config", "alembic.ini", "upgrade", "head"],
        cwd=app_dir,
        check=False,
    )
    if r.returncode != 0:
        return r.returncode

    py_args = [sys.executable, "-m", "pytest", "-v", "--tb=short"]
    if not args.cov:
        py_args.append("--no-cov")
    if args.pytest_args:
        py_args.extend(args.pytest_args)
    else:
        py_args.append("tests/")

    r2 = subprocess.run(py_args, cwd=root, check=False)
    return r2.returncode


if __name__ == "__main__":
    raise SystemExit(main())
