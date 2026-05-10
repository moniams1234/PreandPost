"""matching.py — column name normalisation and fuzzy matching."""
from __future__ import annotations

import pandas as pd


def norm_df(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse multi-space / newline column names."""
    df.columns = [" ".join(str(c).split()) for c in df.columns]
    return df


def fcol(df: pd.DataFrame, *candidates: str) -> str | None:
    """Return first matching column (case-insensitive, space-normalised, Polish-safe)."""
    lc = {" ".join(c.split()).lower(): c for c in df.columns}
    for cand in candidates:
        key = " ".join(cand.split()).lower()
        if key in lc:
            return lc[key]
    # Fuzzy: ignore dashes/underscores/spaces differences
    def _norm(s: str) -> str:
        import re
        return re.sub(r"[\s\-_]+", "", s).lower()

    lc_norm = {_norm(c): c for c in df.columns}
    for cand in candidates:
        key = _norm(cand)
        if key in lc_norm:
            return lc_norm[key]
    return None
