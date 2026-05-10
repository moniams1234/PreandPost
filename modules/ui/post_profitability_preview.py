"""post_profitability_preview.py — Podgląd Profitability page with charts."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.calculations.profitability_engine import exclude_oticon_zam_rows
from modules.ui.shared import section_title, kpi_card, BURG, ORG, GRN, RED, LAYOUT


def render(result: dict, tpm_thr: float, cm_thr: float) -> None:
    st.markdown("# 📋 Podgląd Profitability")

    if not result:
        st.warning("⚠️ Brak danych. Przejdź do **Upload plików** i kliknij **▶ Oblicz**.")
        st.stop()

    df_m = exclude_oticon_zam_rows(result["df_prof"], result.get("klient_col"))
    klient_col = result.get("klient_col")
    grp_col = klient_col or "Zlecenie produkcyjne"

    # ── Filters ───────────────────────────────────────────────────────────────
    section_title("🔍 Filtry")
    f1, f2, f3 = st.columns(3)

    months_all = sorted(df_m["Miesiąc faktury"].dropna().unique())
    sel_months = f1.multiselect("Miesiąc faktury", months_all,
                                 default=months_all, key="_pv_months")

    clients_all = sorted(df_m[grp_col].dropna().unique()) if grp_col in df_m.columns else []
    sel_clients = f2.multiselect("Klient", clients_all, default=clients_all, key="_pv_clients")

    if "Batch" in df_m.columns:
        batches_all = sorted(df_m["Batch"].dropna().unique())
        sel_batch = f3.multiselect("Batch", batches_all, default=batches_all, key="_pv_batch")
    else:
        sel_batch = []

    mask = df_m["Miesiąc faktury"].isin(sel_months) if sel_months else pd.Series(True, index=df_m.index)
    if sel_clients and grp_col in df_m.columns:
        mask &= df_m[grp_col].isin(sel_clients)
    if sel_batch and "Batch" in df_m.columns:
        mask &= df_m["Batch"].isin(sel_batch)
    df_m = df_m[mask]

    # ── KPI row ───────────────────────────────────────────────────────────────
    sv  = df_m["Sales Value"].sum()
    tpm = df_m["TPM"].sum()
    cm  = df_m["CM"].sum()
    tpm_pct = tpm / sv if sv else 0
    cm_pct  = cm  / sv if sv else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(kpi_card(f"{len(df_m):,}", "Rekordów", "b"), unsafe_allow_html=True)
    k2.markdown(kpi_card(f"{sv:,.0f}", "Sales PLN"), unsafe_allow_html=True)
    k3.markdown(kpi_card(f"{tpm:,.0f}", "TPM PLN", "g" if tpm_pct >= tpm_thr / 100 else "r"),
                unsafe_allow_html=True)
    k4.markdown(kpi_card(f"{tpm_pct:.1%}", "TPM %", "g" if tpm_pct >= tpm_thr / 100 else "r"),
                unsafe_allow_html=True)
    k5.markdown(kpi_card(f"{cm_pct:.1%}", "CM %", "g" if cm_pct >= cm_thr / 100 else "r"),
                unsafe_allow_html=True)

    # ── Column selector ───────────────────────────────────────────────────────
    section_title("📊 Tabela")
    all_cols = list(df_m.columns)
    KEY_COLS = ["Numer", "Klient", "Zamówienie", "Zlecenie produkcyjne",
                "Digital/Offset", "Batch", "Sales Value", "Total DL",
                "Total Materials", "TPM", "CM"]
    default_show = [c for c in KEY_COLS if c in all_cols]
    show_cols = st.multiselect("Kolumny", all_cols, default=default_show, key="_pv_cols")

    fmt_map = {}
    for c in (show_cols or all_cols):
        if c in {"Miesiąc faktury", "Data faktury", "Digital/Offset", "Batch",
                 "Numer", "Klient", "Zamówienie"}:
            continue
        elif c in df_m.columns and pd.api.types.is_numeric_dtype(df_m[c]):
            if "%" in c or "pct" in c.lower():
                fmt_map[c] = "{:.1%}"
            else:
                fmt_map[c] = "{:,.0f}"

    if show_cols:
        df_show = df_m[show_cols]
        try:
            st.dataframe(
                df_show.style.format(fmt_map, na_rep="–"),
                use_container_width=True, height=420,
            )
        except Exception:
            st.dataframe(df_show, use_container_width=True, height=420)

    # ── Charts ────────────────────────────────────────────────────────────────
    if grp_col not in df_m.columns or df_m.empty:
        return

    section_title("📈 Wykresy")
    grp = (
        df_m.groupby(grp_col).agg(
            sv=("Sales Value", "sum"),
            tpm=("TPM", "sum"),
            cm=("CM", "sum"),
            n=(grp_col, "count"),
        ).reset_index()
    )
    grp["tpm_pct"] = grp["tpm"] / grp["sv"].replace(0, float("nan"))
    grp["cm_pct"]  = grp["cm"]  / grp["sv"].replace(0, float("nan"))

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        fig = px.bar(grp.sort_values("sv", ascending=False),
                     x=grp_col, y="sv", title="Sales Value wg klientów",
                     color_discrete_sequence=[BURG])
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    with r1c2:
        fig = px.bar(grp.sort_values("tpm_pct", ascending=False),
                     x=grp_col, y="tpm_pct", title="TPM % wg klientów",
                     color_discrete_sequence=[BURG])
        fig.add_hline(y=tpm_thr / 100, line_dash="dash", line_color=ORG,
                      annotation_text=f"Próg {tpm_thr:.0f}%",
                      annotation_font_color=ORG)
        fig.update_layout(**LAYOUT, yaxis_tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True)
    with r1c3:
        fig = px.bar(grp.sort_values("cm_pct", ascending=False),
                     x=grp_col, y="cm_pct", title="CM % wg klientów",
                     color_discrete_sequence=[GRN])
        fig.add_hline(y=cm_thr / 100, line_dash="dash", line_color=RED,
                      annotation_text=f"Próg {cm_thr:.0f}%",
                      annotation_font_color=RED)
        fig.update_layout(**LAYOUT, yaxis_tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True)

    # ── Alerts ────────────────────────────────────────────────────────────────
    section_title("⚠️ Alerty")
    al1, al2 = st.columns(2)
    with al1:
        st.markdown(f"**TPM % poniżej {tpm_thr:.0f}%**")
        atpm = grp[grp["tpm_pct"].fillna(0) < tpm_thr / 100].sort_values("tpm_pct")
        if not atpm.empty:
            st.dataframe(
                atpm[[grp_col, "sv", "tpm", "tpm_pct"]].rename(columns={
                    grp_col: "Klient", "sv": "Sprzedaż", "tpm": "TPM", "tpm_pct": "TPM %",
                }).style.format({"Sprzedaż": "{:,.0f}", "TPM": "{:,.0f}", "TPM %": "{:.1%}"}),
                use_container_width=True,
            )
        else:
            st.success("Brak alertów TPM ✓")
    with al2:
        st.markdown(f"**CM % poniżej {cm_thr:.0f}%**")
        acm = grp[grp["cm_pct"].fillna(0) < cm_thr / 100].sort_values("cm_pct")
        if not acm.empty:
            st.dataframe(
                acm[[grp_col, "sv", "cm", "cm_pct"]].rename(columns={
                    grp_col: "Klient", "sv": "Sprzedaż", "cm": "CM", "cm_pct": "CM %",
                }).style.format({"Sprzedaż": "{:,.0f}", "CM": "{:,.0f}", "CM %": "{:.1%}"}),
                use_container_width=True,
            )
        else:
            st.success("Brak alertów CM ✓")
