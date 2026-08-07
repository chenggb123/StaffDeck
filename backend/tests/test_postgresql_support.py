import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_postgresql_url_is_normalized_to_psycopg() -> None:
    from app.db.database import _normalize_database_url

    assert _normalize_database_url("postgresql://user:pass@db/staffdeck") == (
        "postgresql+psycopg://user:pass@db/staffdeck"
    )
    assert _normalize_database_url("postgres://user:pass@db/staffdeck") == (
        "postgresql+psycopg://user:pass@db/staffdeck"
    )
    assert _normalize_database_url("postgresql+psycopg://user:pass@db/staffdeck") == (
        "postgresql+psycopg://user:pass@db/staffdeck"
    )


@pytest.mark.skipif(
    not os.getenv("STAFFDECK_TEST_POSTGRESQL_URL"),
    reason="STAFFDECK_TEST_POSTGRESQL_URL is not set",
)
def test_postgresql_init_and_seed() -> None:
    code = """
from sqlmodel import Session
from app.db import engine, init_db
from app.db.seed import seed_demo_data
init_db()
with Session(engine) as db:
    seed_demo_data(db)
print("ok")
engine.dispose()
"""
    env = dict(os.environ)
    env["DATABASE_URL"] = os.environ["STAFFDECK_TEST_POSTGRESQL_URL"]
    env["STAFFDECK_ROLE"] = "web"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
