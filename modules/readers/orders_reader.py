"""orders_reader.py — reader for PreKalkulacja Orders file."""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st
from modules.readers.generic_reader import read_with_header_detect
from modules.utils.matching import norm_df, fcol


REQUIRED_COLUMNS = [
    "Numer-Linia", "Wykrojnik", "Format", "Klient",
    "Opis produktu", "Typ produktu", "Zamawiana ilość",
]


def read_prekalk_orders(uf) -> pd.DataFrame | None:
    """Read Orders file with auto header detection."""
    if uf is None:
        return None
    try:
        raw = uf.read()
        uf.seek(0)
        df = read_with_header_detect(raw)
        if df is None:
            return None
        missing = [c for c in REQUIRED_COLUMNS
                   if fcol(df, c, c.replace("-", " "), c.replace(" ", "-")) is None]
        if missing:
            st.warning(f"⚠️ Orders: brakujące kolumny: {', '.join(missing)}")
        return df
    except Exception as exc:
        st.error(f"❌ Błąd wczytywania Orders: {exc}")
        return None
