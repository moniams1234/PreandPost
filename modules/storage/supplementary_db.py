"""SQLite persistence for PostKalkulacja supplementary uploads."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from modules.utils.matching import fcol


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "postkalkulacja.db"


def database_path() -> Path:
    return Path(os.environ.get("POSTKALK_DB_PATH", str(DEFAULT_DB_PATH)))


def _connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS supplementary_records (
            dataset TEXT NOT NULL, record_key TEXT NOT NULL,
            payload TEXT NOT NULL, row_hash TEXT NOT NULL,
            updated_at TEXT NOT NULL, PRIMARY KEY (dataset, record_key)
        )"""
    )
    return connection


def _normalise_key(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split()).casefold()


def upsert_dataframe(
    dataset: str, df: pd.DataFrame | None, key_candidates: Iterable[str]
) -> tuple[pd.DataFrame | None, dict[str, int]]:
    """Upsert rows and return the complete persisted dataset."""
    stats = {"inserted": 0, "updated": 0, "unchanged": 0}
    if df is None:
        return load_dataframe(dataset), stats

    key_column = fcol(df, *key_candidates)
    rows = json.loads(df.to_json(orient="records", date_format="iso", force_ascii=False))
    now = datetime.now(timezone.utc).isoformat()
    with closing(_connect()) as connection:
        with connection:
            for row in rows:
                payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                row_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                natural_key = _normalise_key(row.get(key_column)) if key_column else ""
                record_key = natural_key or f"hash:{row_hash}"
                existing = connection.execute(
                    "SELECT row_hash FROM supplementary_records WHERE dataset = ? AND record_key = ?",
                    (dataset, record_key),
                ).fetchone()
                if existing is None:
                    connection.execute(
                        "INSERT INTO supplementary_records VALUES (?, ?, ?, ?, ?)",
                        (dataset, record_key, payload, row_hash, now),
                    )
                    stats["inserted"] += 1
                elif existing[0] != row_hash:
                    connection.execute(
                        """UPDATE supplementary_records SET payload = ?, row_hash = ?, updated_at = ?
                           WHERE dataset = ? AND record_key = ?""",
                        (payload, row_hash, now, dataset, record_key),
                    )
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1
    return load_dataframe(dataset), stats


def load_dataframe(dataset: str) -> pd.DataFrame | None:
    with closing(_connect()) as connection:
        rows = connection.execute(
            "SELECT payload FROM supplementary_records WHERE dataset = ? ORDER BY updated_at, record_key",
            (dataset,),
        ).fetchall()
    return pd.DataFrame([json.loads(row[0]) for row in rows]) if rows else None
