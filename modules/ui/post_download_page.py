"""PostKalkulacja XLSX download page."""
from __future__ import annotations

import streamlit as st

from modules.exports.profitability_export import build_xlsx


def render(result: dict, rates: dict, click_costs: dict, prepress: dict,
           other_pct: float, tpm_thr: float, cm_thr: float) -> None:
    st.markdown("# ⬇️ Pobierz XLSX — Profitability")

    if not result:
        st.warning("⚠️ Brak danych. Przejdź do **Upload plików** i kliknij **▶ Oblicz**.")
        st.stop()

    df_prof = result["df_prof"]

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        "Wybierz okres i kliknij **Generuj**, aby zbudować kompletny plik XLSX "
        "ze wszystkimi arkuszami i formatowaniem."
    )

    months = (
        sorted(df_prof["Miesiąc faktury"].dropna().astype(str).unique())
        if "Miesiąc faktury" in df_prof.columns else []
    )
    month_from = month_to = None
    file_suffix = "caly_okres"

    if months:
        period_mode = st.radio(
            "Zakres danych",
            ["Cały dostępny okres", "Wybrany okres"],
            horizontal=True,
            key="_post_export_period_mode",
        )
        if period_mode == "Wybrany okres":
            period_cols = st.columns(2)
            month_from = period_cols[0].selectbox(
                "Od miesiąca", months, index=0, key="_post_export_month_from"
            )
            valid_months_to = [month for month in months if month >= month_from]
            month_to = period_cols[1].selectbox(
                "Do miesiąca", valid_months_to, index=len(valid_months_to) - 1,
                key="_post_export_month_to",
            )
            file_suffix = (
                month_from if month_from == month_to
                else f"{month_from}_do_{month_to}"
            )
            selected_count = df_prof["Miesiąc faktury"].astype(str).between(
                month_from, month_to
            ).sum()
            st.caption(f"Do eksportu: {selected_count:,} rekordów.")

    if st.button("🔄 Generuj plik XLSX", key="_post_gen_xlsx"):
        with st.spinner("Budowanie pliku XLSX…"):
            xlsx_buf = build_xlsx(
                result, rates, click_costs, prepress, other_pct, tpm_thr, cm_thr,
                month_from=month_from, month_to=month_to,
            )
        st.success("✅ Plik gotowy!")
        st.download_button(
            label="⬇️ Pobierz plik XLSX",
            data=xlsx_buf,
            file_name=f"Profitability_{file_suffix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="_post_dl_btn",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### 📊 Szybkie statystyki")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rekordów", f"{len(df_prof):,}")
    m2.metric(
        "Miesięcy",
        df_prof["Miesiąc faktury"].nunique()
        if "Miesiąc faktury" in df_prof.columns else 0,
    )
    m3.metric(
        "Sprzedaż (PLN)",
        f"{df_prof['Sales Value'].sum():,.0f}"
        if "Sales Value" in df_prof.columns else "–",
    )
    m4.metric(
        "TPM (PLN)",
        f"{df_prof['TPM'].sum():,.0f}" if "TPM" in df_prof.columns else "–",
    )
