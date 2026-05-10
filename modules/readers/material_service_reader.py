"""material_service_reader.py — reader for Usługa na surowcu / Gilotyna file."""
from __future__ import annotations

import re
import io
import pandas as pd
import streamlit as st
from modules.readers.generic_reader import read_with_header_detect
from modules.utils.matching import norm_df, fcol


def _extract_mindex(val: str) -> str | None:
    """Extract text between [ and ] from Surowiec column."""
    m = re.search(r"\[([^\]]+)\]", str(val))
    return m.group(1).strip() if m else None


def _extract_cuts(val: str) -> float | None:
    """Extract number of cuts from text before first * × x X."""
    s = str(val).strip()
    m = re.match(r"^\s*([\d.,]+)\s*[xX*×]", s)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return None


def read_prekalk_material_service(uf) -> pd.DataFrame | None:
    """
    Read Material Service (Gilotyna) file.
    Adds computed columns: mindex, liczba_cięć.
    """
    if uf is None:
        return None
    try:
        raw = uf.read()
        uf.seek(0)
        df = read_with_header_detect(raw)
        if df is None:
            return None
        df = norm_df(df)

        # The mindex column might already exist or come from Surowiec.1
        sur_c = fcol(df, "Surowiec.1", "Surowiec", "Material", "Materiał")
        if sur_c:
            df["mindex"] = df[sur_c].astype(str).apply(_extract_mindex)
            df["liczba_cięć"] = df[sur_c].astype(str).apply(_extract_cuts)
        else:
            st.warning("⚠️ Usługa na surowcu: brak kolumny Surowiec — mindex/cięcia niewyznaczone.")

        return df
    except Exception as exc:
        st.error(f"❌ Błąd wczytywania Usługi na surowcu: {exc}")
        return None
