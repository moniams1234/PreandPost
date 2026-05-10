"""tools_reader.py — reader for Tools (Wykrojniki) file."""
from __future__ import annotations

import os
import io
import pandas as pd
import streamlit as st
from modules.readers.generic_reader import read_with_header_detect
from modules.utils.matching import norm_df, fcol

_DEFAULT_TOOLS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "default_tools.xlsx"
)
_FALLBACK_TOOLS_PATH = "/mnt/user-data/uploads/tool_list__16_.xlsx"

TOOLS_COLS = [
    "Nazwa narzędzia",
    "Typ narzędzia",
    "Klient",
    "Ilość użytków wykrojnika / Nesting",
]


def _extract_tools_cols(df: pd.DataFrame) -> pd.DataFrame:
    nm = fcol(df, "Nazwa narzędzia")
    tp = fcol(df, "Typ narzędzia")
    kl = fcol(df, "Klient")
    ne = fcol(
        df,
        "Ilość użytków wykrojnika / Nesting",
        "Ilość użytków wykrojnika/Nesting",
        "ilośc użytków.",
        "ilość użytków",
        "nesting",
    )
    rename = {}
    if nm:
        rename[nm] = "Nazwa narzędzia"
    if tp:
        rename[tp] = "Typ narzędzia"
    if kl:
        rename[kl] = "Klient"
    if ne:
        rename[ne] = "Ilość użytków wykrojnika / Nesting"
    out = df.rename(columns=rename)
    for col in TOOLS_COLS:
        if col not in out.columns:
            out[col] = None
    return out[TOOLS_COLS].copy()


def _load_from_path(path: str) -> pd.DataFrame | None:
    if not os.path.exists(path):
        return None
    try:
        raw = open(path, "rb").read()
        df = read_with_header_detect(raw)
        if df is None:
            return None
        return _extract_tools_cols(norm_df(df))
    except Exception:
        return None


def read_prekalk_tools(uf) -> pd.DataFrame | None:
    """Read Tools file. Falls back to bundled defaults."""
    if uf is None:
        df = _load_from_path(_DEFAULT_TOOLS_PATH)
        if df is None:
            df = _load_from_path(_FALLBACK_TOOLS_PATH)
        return df
    try:
        raw = uf.read()
        uf.seek(0)
        df = read_with_header_detect(raw)
        if df is None:
            return None
        return _extract_tools_cols(norm_df(df))
    except Exception as exc:
        st.error(f"❌ Błąd wczytywania Tools: {exc}")
        return None


def empty_tools_df() -> pd.DataFrame:
    return pd.DataFrame(columns=TOOLS_COLS)
