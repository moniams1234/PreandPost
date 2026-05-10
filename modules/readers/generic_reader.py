"""generic_reader.py — auto-header-detection reader for Excel files."""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st
from modules.utils.matching import norm_df


def read_with_header_detect(
    raw: bytes,
    sheet: int | str = 0,
    bad_words: tuple[str, ...] = (
        "export", "postkalkulacja", "lista zamkniętych",
        "lista zamknietych", "system, z dnia", "raport",
    ),
) -> pd.DataFrame | None:
    """Read Excel bytes with automatic header-row detection."""
    try:
        probe = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, header=None, nrows=15)
        hrow = 0
        for i, row in probe.iterrows():
            vals = [str(v).strip() for v in row.dropna()]
            if len(vals) >= 3 and not any(
                any(bad in v.lower() for bad in bad_words) for v in vals
            ):
                hrow = i
                break
        df = pd.read_excel(io.BytesIO(raw), sheet_name=sheet, header=hrow)
        return norm_df(df)
    except Exception as exc:
        st.warning(f"⚠️ Błąd wczytywania pliku (arkusz {sheet}): {exc}")
        return None


def read_generic(uf, sheet: int | str = 0) -> pd.DataFrame | None:
    """Generic file-object reader."""
    if uf is None:
        return None
    try:
        raw = uf.read()
        uf.seek(0)
        return read_with_header_detect(raw, sheet=sheet)
    except Exception as exc:
        st.warning(f"⚠️ Błąd wczytywania pliku: {exc}")
        return None
