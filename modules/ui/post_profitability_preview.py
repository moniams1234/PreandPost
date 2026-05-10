"""post_profitability_preview.py — Podgląd Profitability page.

This page intentionally follows the simpler visual/filter layout from app (6):
- top summary card,
- four filters with "(wszystkie)/(wszyscy)" default chips,
- full Profitability table preview.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.calculations.profitability_engine import exclude_oticon_zam_rows


def render(result: dict, tpm_thr: float, cm_thr: float) -> None:
    st.markdown("# 📋 Podgląd Profitability")

    if not result:
        st.warning("⚠️ Brak danych. Przejdź do zakładki **Upload plików** i kliknij **▶ Oblicz**.")
        st.stop()

    klient_c = result.get("klient_col")
    df_prof = exclude_oticon_zam_rows(result["df_prof"], klient_c)
    warns = result.get("warns", [])
    for w in warns:
        st.warning(w)

    n_rec = len(df_prof)
    n_col = len(df_prof.columns)
    n_mon = df_prof["Miesiąc faktury"].nunique() if "Miesiąc faktury" in df_prof.columns else 0
    sv_sum = df_prof["Sales Value"].sum() if "Sales Value" in df_prof.columns else 0

    st.markdown(
        f'<div class="card"><b>{n_rec:,}</b> rekordów &nbsp;|&nbsp; '
        f'<b>{n_col}</b> kolumn &nbsp;|&nbsp; '
        f'<b>{n_mon}</b> miesięcy &nbsp;|&nbsp; '
        f'Sprzedaż: <b>{sv_sum:,.0f} PLN</b></div>',
        unsafe_allow_html=True,
    )

    # ── Filters exactly like app (6): default chips are "(wszystkie)" / "(wszyscy)"
    fc1, fc2, fc3, fc4 = st.columns(4)

    months_av = sorted(df_prof["Miesiąc faktury"].dropna().astype(str).unique()) if "Miesiąc faktury" in df_prof.columns else []
    sel_m = fc1.multiselect(
        "Miesiące",
        ["(wszystkie)"] + months_av,
        default=["(wszystkie)"],
        key="_pv_miesiace_app6",
    )

    if klient_c and klient_c in df_prof.columns:
        clients_av = sorted(df_prof[klient_c].dropna().astype(str).unique())
        sel_cl = fc2.multiselect(
            "Klient",
            ["(wszyscy)"] + clients_av,
            default=["(wszyscy)"],
            key="_pv_klient_app6",
        )
    else:
        sel_cl = ["(wszyscy)"]

    if "Digital/Offset" in df_prof.columns:
        do_av = sorted(df_prof["Digital/Offset"].dropna().astype(str).unique())
        sel_do = fc3.multiselect(
            "Digital/Offset",
            ["(wszystkie)"] + do_av,
            default=["(wszystkie)"],
            key="_pv_do_app6",
        )
    else:
        sel_do = ["(wszystkie)"]

    if "Batch" in df_prof.columns:
        batch_av = sorted(df_prof["Batch"].dropna().astype(str).unique())
        sel_bat = fc4.multiselect(
            "Batch",
            ["(wszystkie)"] + batch_av,
            default=["(wszystkie)"],
            key="_pv_batch_app6",
        )
    else:
        sel_bat = ["(wszystkie)"]

    dv = df_prof.copy()
    if "(wszystkie)" not in sel_m and sel_m and "Miesiąc faktury" in dv.columns:
        dv = dv[dv["Miesiąc faktury"].astype(str).isin(sel_m)]
    if "(wszyscy)" not in sel_cl and sel_cl and klient_c and klient_c in dv.columns:
        dv = dv[dv[klient_c].astype(str).isin(sel_cl)]
    if "(wszystkie)" not in sel_do and sel_do and "Digital/Offset" in dv.columns:
        dv = dv[dv["Digital/Offset"].astype(str).isin(sel_do)]
    if "(wszystkie)" not in sel_bat and sel_bat and "Batch" in dv.columns:
        dv = dv[dv["Batch"].astype(str).isin(sel_bat)]

    st.markdown(f"Pokazuję **{len(dv):,}** rekordów.")
    st.dataframe(dv, use_container_width=True, height=540)
