"""post_summary_page.py — Podsumowanie page."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.calculations.profitability_engine import exclude_oticon_zam_rows
from modules.ui.shared import section_title, BURG, ORG, GRN, LAYOUT


def render(result: dict, tpm_thr: float, cm_thr: float) -> None:
    st.markdown("# 📈 Podsumowanie")

    if not result:
        st.warning("⚠️ Brak danych. Przejdź do **Upload plików** i kliknij **▶ Oblicz**.")
        st.stop()

    df_all = exclude_oticon_zam_rows(result["df_prof"], result.get("klient_col"))
    klient_col = result.get("klient_col")
    grp_col = klient_col or "Zlecenie produkcyjne"

    months_all = sorted(df_all["Miesiąc faktury"].dropna().unique())
    sel_month = st.selectbox("Wybierz miesiąc", months_all, key="_sum_month") if months_all else None
    if sel_month is None:
        st.info("Brak danych do wyświetlenia.")
        return

    df_m = df_all[df_all["Miesiąc faktury"] == sel_month].copy()
    if grp_col in df_m.columns:
        df_m[grp_col] = df_m[grp_col].fillna("(brak)")

    if df_m.empty or grp_col not in df_m.columns:
        st.info(f"Brak danych dla {sel_month}.")
        return

    rows = []
    for kl, grp in df_m.groupby(grp_col):
        sv = grp["Sales Value"].sum()
        tpm = grp["TPM"].sum()
        cm = grp["CM"].sum()
        rows.append({
            "Klient": kl, "Miesiąc": sel_month,
            "Suma sprzedaży": sv, "Suma TPM": tpm,
            "TPM %": tpm / sv if sv else 0,
            "Suma CM": cm,
            "CM %": cm / sv if sv else 0,
            "Zamówień": len(grp),
        })
    df_s = pd.DataFrame(rows)

    section_title("📋 Tabela podsumowania")
    try:
        st.dataframe(
            df_s.style
            .format({"Suma sprzedaży": "{:,.0f}", "Suma TPM": "{:,.0f}",
                     "TPM %": "{:.1%}", "Suma CM": "{:,.0f}", "CM %": "{:.1%}"})
            .applymap(
                lambda v: "background-color: #ffd6d6; color: #900"
                if isinstance(v, float) and v < tpm_thr / 100 else "",
                subset=["TPM %"],
            )
            .applymap(
                lambda v: "background-color: #ffd6d6; color: #900"
                if isinstance(v, float) and v < cm_thr / 100 else "",
                subset=["CM %"],
            ),
            use_container_width=True,
        )
    except Exception:
        st.dataframe(df_s, use_container_width=True)

    section_title("📊 Wykresy")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(df_s.sort_values("Suma sprzedaży", ascending=False),
                     x="Klient", y="Suma sprzedaży",
                     title=f"Sales Value — {sel_month}",
                     color_discrete_sequence=[BURG])
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(df_s.sort_values("TPM %", ascending=False),
                     x="Klient", y="TPM %",
                     title=f"TPM % — {sel_month}",
                     color_discrete_sequence=[GRN])
        fig.add_hline(y=tpm_thr / 100, line_dash="dash", line_color=ORG)
        fig.update_layout(**LAYOUT, yaxis_tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True)
