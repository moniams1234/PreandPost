"""tektura_reader.py — reader for Tektura CSV/XLSX file."""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st
from modules.readers.generic_reader import read_with_header_detect
from modules.utils.matching import norm_df, fcol


def read_prekalk_tektura(uf) -> pd.DataFrame | None:
    """Read Tektura CSV or XLSX file."""
    if uf is None:
        return None
    try:
        raw = uf.read()
        uf.seek(0)
        name = getattr(uf, "name", "")

        if name.lower().endswith(".csv"):
            df = None
            for sep in [";", ",", "\t"]:
                try:
                    df = pd.read_csv(io.BytesIO(raw), sep=sep)
                    if df.shape[1] >= 3:
                        break
                except Exception:
                    continue
            if df is None or df.shape[1] < 3:
                st.warning("⚠️ Tektura CSV: nie rozpoznano separatora.")
                return None
            df = norm_df(df)
        else:
            df = read_with_header_detect(raw)
            if df is None:
                return None

        # Normalise the price column to float
        val_col = fcol(df, "(m.value/ m.qty)", "m.value/ m.qty",
                       "m.value/m.qty", "value/qty", "cena tektury")
        if val_col:
            df[val_col] = pd.to_numeric(
                df[val_col].astype(str).str.replace(",", "."),
                errors="coerce",
            ).fillna(0)
        return df
    except Exception as exc:
        st.error(f"❌ Błąd wczytywania Tektury: {exc}")
        return None
