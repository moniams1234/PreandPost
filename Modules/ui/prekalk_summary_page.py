"""prekalk_summary_page.py — PreKalkulacja Podsumowanie page."""
from __future__ import annotations

import plotly.express as px
import streamlit as st
from modules.calculations.summaries import build_prekalk_summary
from modules.ui.shared import section_title, BURG, ORG, GRN, RED, LAYOUT


def render() -> None:
    st.markdown("# 📈 PreKalkulacja — Podsumowanie")

    pk_res = st.session_state.get("pk_result")
    if pk_res is None:
        st.warning("⚠️ Brak danych. Przejdź do **PreKalkulacja – Upload** i przelicz.")
        st.stop()

    df_pk = pk_res["df_pk"]
    tpm_thr = st.session_state.get("tpm_thr", 60.0)
    cm_thr  = st.session_state.get("cm_thr",  40.0)

    df_sum = build_prekalk_summary(df_pk)
    if df_sum.empty:
        st.info("Brak danych do podsumowania.")
        return

    months = sorted(df_sum["Miesiąc faktury"].dropna().unique())
    sel_month = st.selectbox("Wybierz miesiąc", ["(wszystkie)"] + list(months),
                              key="_pk_sum_month")

    if sel_month != "(wszystkie)":
        df_show = df_sum[df_sum["Miesiąc faktury"] == sel_month]
    else:
        df_show = df_sum

    section_title("📋 Tabela podsumowania")
    try:
        st.dataframe(
            df_show.style
            .format({
                "Sales Value": "{:,.0f}", "TPM": "{:,.0f}", "CM": "{:,.0f}",
                "TPM%": "{:.1%}", "CM%": "{:.1%}",
            })
            .applymap(
                lambda v: "background-color:#ffd6d6;color:#900"
                if isinstance(v, float) and v < tpm_thr / 100 else "",
                subset=["TPM%"],
            )
            .applymap(
                lambda v: "background-color:#ffd6d6;color:#900"
                if isinstance(v, float) and v < cm_thr / 100 else "",
                subset=["CM%"],
            ),
            use_container_width=True,
        )
    except Exception:
        st.dataframe(df_show, use_container_width=True)

    section_title("📊 Wykresy")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(df_show.sort_values("Sales Value", ascending=False),
                     x="Nazwa klienta", y="Sales Value",
                     title="Sales Value wg klientów",
                     color_discrete_sequence=[BURG])
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(df_show.sort_values("TPM%", ascending=False),
                     x="Nazwa klienta", y="TPM%",
                     title="TPM% wg klientów",
                     color_discrete_sequence=[GRN])
        fig.add_hline(y=tpm_thr / 100, line_dash="dash", line_color=RED,
                      annotation_text=f"Próg {tpm_thr:.0f}%")
        fig.update_layout(**LAYOUT, yaxis_tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True)
