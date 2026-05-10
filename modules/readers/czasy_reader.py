"""czasy_reader.py — reader for Czasy dla aplikacji (times) file."""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st
from modules.readers.generic_reader import read_with_header_detect
from modules.utils.matching import norm_df


def read_czasy(uf) -> pd.DataFrame | None:
    """Read czasy file — returns raw DataFrame."""
    if uf is None:
        return None
    try:
        raw = uf.read()
        uf.seek(0)
        return read_with_header_detect(raw, sheet=0)
    except Exception as exc:
        st.warning(f"⚠️ Błąd wczytywania Czasy: {exc}")
        return None


def read_czasy_pivot(uf) -> pd.DataFrame | None:
    """
    Read PIVOT sheet from czasy file.
    Returns None if sheet is not found.
    """
    if uf is None:
        return None
    try:
        raw = uf.read()
        uf.seek(0)
        xl = pd.ExcelFile(io.BytesIO(raw))
        pivot_sheet = next(
            (s for s in xl.sheet_names if "pivot" in s.lower()),
            xl.sheet_names[0],
        )
        # Detect header row
        probe = pd.read_excel(io.BytesIO(raw), sheet_name=pivot_sheet,
                               header=None, nrows=5)
        first_row = [str(v).strip() for v in probe.iloc[0].dropna()]
        has_header = any(
            "numer" in v.lower() or "nazwa" in v.lower() or "data" in v.lower()
            for v in first_row
        )
        hrow = 0 if has_header else 1
        df = pd.read_excel(io.BytesIO(raw), sheet_name=pivot_sheet, header=hrow)
        return norm_df(df)
    except Exception as exc:
        st.warning(f"⚠️ Błąd wczytywania arkusza PIVOT z Czasy: {exc}")
        return None


def read_stawki(uf) -> dict[str, float]:
    """Parse Stawki file → {machine_name: hourly_rate}."""
    if uf is None:
        return {}
    try:
        from modules.utils.matching import fcol
        from modules.utils.helpers import sn
        raw = uf.read()
        uf.seek(0)
        probe = pd.read_excel(io.BytesIO(raw), header=None, nrows=15)
        hrow = 0
        for i, row in probe.iterrows():
            vals = [str(v).strip().lower() for v in row.dropna()]
            if (any("nazwa maszyny" in v or "maszyna" == v for v in vals)
                    and any("stawka" in v for v in vals)):
                hrow = i
                break
        df = pd.read_excel(io.BytesIO(raw), header=hrow)
        df = norm_df(df)
        nm = fcol(df, "Nazwa maszyny", "Maszyna", "Machine", "Machine name")
        sr = fcol(df, "Stawka rbg", "Stawka rbg (PLN/h)", "RBG", "Rate",
                  "Hourly rate", "PLN/h")
        if not (nm and sr):
            return {}
        return {
            str(r[nm]).strip(): sn(r[sr])
            for _, r in df.dropna(subset=[nm]).iterrows()
            if str(r[nm]).strip()
        }
    except Exception as exc:
        st.warning(f"⚠️ Błąd stawek rbg: {exc}")
        return {}
