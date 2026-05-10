"""wydajnosc_reader.py — reader for Wydajność (machine efficiency) file."""
from __future__ import annotations

import os
import io
import pandas as pd
import streamlit as st
from modules.readers.generic_reader import read_with_header_detect
from modules.utils.matching import norm_df, fcol
from modules.utils.helpers import sn

_DEFAULT_WYDAJNOSC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "default_wydajnosc.xlsx"
)
_FALLBACK_WYDAJNOSC_PATH = "/mnt/user-data/uploads/Wydajnośc.xlsx"

WYDAJNOSC_COLS = ["Nazwa maszyny", "Stawka rbg", "Set Up czas", "Wydajność", "Miara"]


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    nm = fcol(df, "Nazwa maszyny")
    sr = fcol(df, "Stawka rbg", "Stawka rbg (PLN/h)", "Rate")
    su = fcol(df, "SetUp czas w minutach", "Set Up czas", "SetUp czas", "Setup")
    wy = fcol(df, "Wydajnośc", "Wydajność", "Wydajnosc", "Efficiency")
    mi = fcol(df, "Unnamed: 6", "Miara", "Jednostka", "Unit")
    rename = {}
    if nm:
        rename[nm] = "Nazwa maszyny"
    if sr:
        rename[sr] = "Stawka rbg"
    if su:
        rename[su] = "Set Up czas"
    if wy:
        rename[wy] = "Wydajność"
    if mi:
        rename[mi] = "Miara"
    df = df.rename(columns=rename)
    for col in WYDAJNOSC_COLS:
        if col not in df.columns:
            df[col] = None
    df = df.dropna(subset=["Nazwa maszyny"])
    df["Stawka rbg"] = pd.to_numeric(df["Stawka rbg"], errors="coerce").fillna(0)
    df["Wydajność"] = pd.to_numeric(df["Wydajność"], errors="coerce").fillna(0)
    df["Set Up czas"] = pd.to_numeric(df["Set Up czas"], errors="coerce").fillna(0)
    return df[WYDAJNOSC_COLS].copy()


def _load_from_path(path: str) -> pd.DataFrame | None:
    if not os.path.exists(path):
        return None
    try:
        raw = open(path, "rb").read()
        df = read_with_header_detect(raw)
        if df is None:
            return None
        return _normalise(norm_df(df))
    except Exception:
        return None


def read_prekalk_wydajnosc(uf) -> pd.DataFrame | None:
    """Read Wydajność file. Falls back to bundled defaults."""
    if uf is None:
        df = _load_from_path(_DEFAULT_WYDAJNOSC_PATH)
        if df is None:
            df = _load_from_path(_FALLBACK_WYDAJNOSC_PATH)
        return df
    try:
        raw = uf.read()
        uf.seek(0)
        df = read_with_header_detect(raw)
        if df is None:
            return None
        return _normalise(norm_df(df))
    except Exception as exc:
        st.error(f"❌ Błąd wczytywania Wydajności: {exc}")
        return None


def empty_wydajnosc_df() -> pd.DataFrame:
    return pd.DataFrame(columns=WYDAJNOSC_COLS)


def wydajnosc_as_dict(df: pd.DataFrame) -> dict[str, dict]:
    """Return {machine_name: row_dict} for fast lookup."""
    if df is None or df.empty:
        return {}
    return {
        str(r["Nazwa maszyny"]).strip(): r.to_dict()
        for _, r in df.iterrows()
        if pd.notna(r.get("Nazwa maszyny"))
    }
