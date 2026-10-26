import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_alembic(database_url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": database_url}
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", *args], cwd=ROOT, env=env, check=True, capture_output=True
    )


def names(db_file: Path, kind: str) -> set[str]:
    with sqlite3.connect(db_file) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type=?", (kind,))}


def test_migration_creates_and_removes_the_links_table(tmp_path):
    db_file = tmp_path / "migration.db"
    url = f"sqlite:///{db_file}"

    run_alembic(url, "upgrade", "head")
    assert "links" in names(db_file, "table")
    assert "ix_links_code" in names(db_file, "index")

    run_alembic(url, "downgrade", "base")
    assert "links" not in names(db_file, "table")
