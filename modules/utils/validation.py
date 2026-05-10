"""validation.py — DataFrame validation helpers."""
from __future__ import annotations

import pandas as pd
from modules.utils.matching import fcol


def check_required_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    """Return list of missing column names."""
    missing = []
    for col in required:
        if fcol(df, col) is None:
            missing.append(col)
    return missing
