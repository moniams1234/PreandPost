"""post_dashboard_page.py — Kokpit (dashboard) page."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.calculations.profitability_engine import exclude_oticon_zam_rows
from modules.ui.shared import section_title, kpi_card, BURG, ORG, GRN, RED, LAYOUT


def render(result: dict, tpm_thr: float, cm_thr: float) -> None:
    st.markdown("# 🎯 Kokpit")

    if not result:
        st.warning("⚠️ Brak danych. Przejdź do **Upload plików** i kliknij **▶ Oblicz**.")
        st.stop()

    df_all = exclude_oticon_zam_rows(result["df_prof"], result.get("klient_col"))
    klient_col = result.get("klient_col")
    grp_col = klient_col or "Zlecenie produkcyjne"

    # ── Month filter ──────────────────────────────────────────────────────────
    months_all = sorted(df_all["Miesiąc faktury"].dropna().unique())
    sel_months = st.multiselect("Filtruj miesiące", months_all,
                                 default=months_all, key="_kok_months")
    if sel_months:
        df_all = df_all[df_all["Miesiąc faktury"].isin(sel_months)]

    if df_all.empty:
        st.info("Brak danych dla wybranych miesięcy.")
        return

    # ── Global KPIs ───────────────────────────────────────────────────────────
    sv  = df_all["Sales Value"].sum()
    tpm = df_all["TPM"].sum()
    cm  = df_all["CM"].sum()
    tpm_pct = tpm / sv if sv else 0
    cm_pct  = cm  / sv if sv else 0

    section_title("🔢 Łączne KPI")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.markdown(kpi_card(f"{len(df_all):,}", "Rekordów", "b"), unsafe_allow_html=True)
    k2.markdown(kpi_card(f"{sv:,.0f}", "Sales PLN"), unsafe_allow_html=True)
    k3.markdown(kpi_card(f"{tpm:,.0f}", "TPM PLN", "g" if tpm_pct >= tpm_thr / 100 else "r"),
                unsafe_allow_html=True)
    k4.markdown(kpi_card(f"{tpm_pct:.1%}", "TPM %", "g" if tpm_pct >= tpm_thr / 100 else "r"),
                unsafe_allow_html=True)
    k5.markdown(kpi_card(f"{cm:,.0f}", "CM PLN", "g" if cm_pct >= cm_thr / 100 else "r"),
                unsafe_allow_html=True)
    k6.markdown(kpi_card(f"{cm_pct:.1%}", "CM %", "g" if cm_pct >= cm_thr / 100 else "r"),
                unsafe_allow_html=True)

    # ── Monthly trend ─────────────────────────────────────────────────────────
    section_title("📅 Trend miesięczny")
    kok_rows = []
    for month in sorted(df_all["Miesiąc faktury"].dropna().unique()):
        df_mo = df_all[df_all["Miesiąc faktury"] == month]
        sv_m  = df_mo["Sales Value"].sum()
        tpm_m = df_mo["TPM"].sum()
        cm_m  = df_mo["CM"].sum()
        kok_rows.append({
            "Miesiąc": month, "Sprzedaż": sv_m,
            "TPM": tpm_m, "TPM %": tpm_m / sv_m if sv_m else 0,
            "CM": cm_m,   "CM %": cm_m / sv_m if sv_m else 0,
            "Klientów": df_mo[grp_col].nunique() if grp_col in df_mo.columns else 0,
            "Zamówień": len(df_mo),
        })
    df_kok = pd.DataFrame(kok_rows)

    try:
        st.dataframe(
            df_kok.style.format({
                "Sprzedaż": "{:,.0f}", "TPM": "{:,.0f}", "CM": "{:,.0f}",
                "TPM %": "{:.1%}", "CM %": "{:.1%}",
            }),
            use_container_width=True,
        )
    except Exception:
        st.dataframe(df_kok, use_container_width=True)

    if not df_kok.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(df_kok, x="Miesiąc", y="Sprzedaż",
                          title="Sprzedaż miesięczna",
                          color_discrete_sequence=[BURG], markers=True)
            fig.update_layout(**LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.line(df_kok, x="Miesiąc", y=["TPM %", "CM %"],
                          title="TPM% i CM% miesięcznie", markers=True,
                          color_discrete_sequence=[GRN, ORG])
            fig.add_hline(y=tpm_thr / 100, line_dash="dash", line_color=RED,
                          annotation_text=f"TPM próg {tpm_thr:.0f}%")
            fig.add_hline(y=cm_thr / 100, line_dash="dash", line_color="gray",
                          annotation_text=f"CM próg {cm_thr:.0f}%")
            fig.update_layout(**LAYOUT, yaxis_tickformat=".1%")
            st.plotly_chart(fig, use_container_width=True)

    # ── Digital/Offset breakdown ──────────────────────────────────────────────
    if "Digital/Offset" in df_all.columns:
        section_title("🖨️ Digital vs Offset")
        do_counts = df_all["Digital/Offset"].value_counts().reset_index()
        do_counts.columns = ["Typ", "Liczba"]
        fig = px.pie(do_counts, names="Typ", values="Liczba",
                     title="Podział Digital / Offset / No printing",
                     color_discrete_sequence=[BURG, ORG, GRN])
        fig.update_layout(height=320, margin=dict(t=42, b=20))
        st.plotly_chart(fig, use_container_width=True)
