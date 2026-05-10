"""machine_costs.py — build the 'maszyny' sheet from czasy PIVOT + wydajnosc."""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from modules.readers.czasy_reader import read_czasy_pivot
from modules.utils.matching import fcol, norm_df
from modules.utils.helpers import sn
from modules.readers.wydajnosc_reader import wydajnosc_as_dict

PIVOT_COLS = [
    "Data zamkniecia zlecenia produkcyjnego",
    "Zakonczenie czynnosci",
    "Nazwa produktu linii Zamowienia",
    "Numer zlecenia produkcyjnego",
    "Nazwa maszyny",
    "Maksimum z Naklad do wykonania Zlecenia Produkcyjnego",
    "Maksimum z Naklad wykonany Zlecenia Produkcyjnego",
    "Suma z Czas czynnosci [min]",
    "Suma z Ilosc netto linii raportu",
    "Suma z Ilosc odpadu w linii raportu",
]


def build_maszyny_sheet(uf_czasy, df_wydajnosc: pd.DataFrame | None) -> pd.DataFrame | None:
    """
    Build the 'maszyny' sheet from czasy PIVOT sheet,
    then join Wydajnosc (Wydajność + Miara).
    """
    if uf_czasy is None:
        return None

    df_pivot = read_czasy_pivot(uf_czasy)
    if df_pivot is None:
        return None

    # Fuzzy-select columns
    selected = {}
    for wanted in PIVOT_COLS:
        found = fcol(df_pivot, wanted,
                     wanted.replace(" z ", " "),
                     wanted.replace("Suma z ", "").strip(),
                     wanted.replace("Maksimum z ", "").strip())
        if found and found not in selected.values():
            selected[wanted] = found

    if not selected:
        st.warning("⚠️ Brak rozpoznanych kolumn w arkuszu PIVOT — arkusz maszyny pominięty.")
        return None

    # Build output with canonical names
    df_out = pd.DataFrame()
    for canonical, actual in selected.items():
        df_out[canonical] = df_pivot[actual].values

    # Remaining unmatched cols (keep raw)
    matched_actuals = set(selected.values())
    for col in df_pivot.columns:
        if col not in matched_actuals and col not in df_out.columns:
            df_out[col] = df_pivot[col].values

    # Join wydajnosc
    if df_wydajnosc is not None and "Nazwa maszyny" in df_out.columns:
        wy_map = wydajnosc_as_dict(df_wydajnosc)

        def _get_wy(mach, col):
            r = wy_map.get(str(mach).strip(), {})
            return r.get(col)

        df_out["Wydajność"] = df_out["Nazwa maszyny"].apply(lambda m: _get_wy(m, "Wydajność"))
        df_out["Miara"] = df_out["Nazwa maszyny"].apply(lambda m: _get_wy(m, "Miara"))

    return df_out
