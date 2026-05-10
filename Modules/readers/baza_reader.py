"""baza_reader.py — reader for Baza / post_list file."""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st
from modules.utils.matching import norm_df


def read_post_list(uf) -> pd.DataFrame | None:
    """
    Read post_list / Baza file.
    The first 3 rows are title/meta rows; actual header is at row index 3.
    """
    if uf is None:
        return None
    try:
        raw = uf.read()
        uf.seek(0)
        df = pd.read_excel(io.BytesIO(raw), header=3)
        return norm_df(df)
    except Exception as exc:
        st.error(f"❌ Błąd wczytywania Bazy: {exc}")
        return None
