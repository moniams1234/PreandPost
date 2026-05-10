"""post_download_page.py — Pobierz XLSX page (PostKalkulacja)."""
from __future__ import annotations

import streamlit as st
from modules.exports.profitability_export import build_xlsx


def render(result: dict, rates: dict, click_costs: dict, prepress: dict,
           other_pct: float, tpm_thr: float, cm_thr: float) -> None:
    st.markdown("# ⬇️ Pobierz XLSX — Profitability")

    if not result:
        st.warning("⚠️ Brak danych. Przejdź do **Upload plików** i kliknij **▶ Oblicz**.")
        st.stop()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        "Kliknij **Generuj**, aby zbudować kompletny plik XLSX "
        "ze wszystkimi arkuszami i formatowaniem."
    )

    if st.button("🔄 Generuj plik XLSX", key="_post_gen_xlsx"):
        with st.spinner("Budowanie pliku XLSX…"):
            xlsx_buf = build_xlsx(result, rates, click_costs, prepress,
                                  other_pct, tpm_thr, cm_thr)
        st.success("✅ Plik gotowy!")
        st.download_button(
            label="⬇️ Pobierz Profitability.xlsx",
            data=xlsx_buf,
            file_name="Profitability.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="_post_dl_btn",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    df_prof = result["df_prof"]
    st.markdown("#### 📊 Szybkie statystyki")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rekordów",        f"{len(df_prof):,}")
    m2.metric("Miesięcy",         df_prof["Miesiąc faktury"].nunique()
              if "Miesiąc faktury" in df_prof.columns else 0)
    m3.metric("Sprzedaż (PLN)",  f"{df_prof['Sales Value'].sum():,.0f}"
              if "Sales Value" in df_prof.columns else "–")
    m4.metric("TPM (PLN)",       f"{df_prof['TPM'].sum():,.0f}"
              if "TPM" in df_prof.columns else "–")
