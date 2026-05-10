"""post_summary_page.py — PostKalkulacja Podsumowanie in app(6) layout."""
from __future__ import annotations

import streamlit as st

from modules.calculations.profitability_engine import exclude_oticon_zam_rows
from modules.ui.app6_views import render_app6_summary


def render(result: dict, tpm_thr: float, cm_thr: float) -> None:
    st.markdown("# 📈 Podsumowanie")

    if not result:
        st.warning("⚠️ Brak danych. Przejdź do **Upload plików** i kliknij **▶ Oblicz**.")
        st.stop()

    df_all = exclude_oticon_zam_rows(result["df_prof"], result.get("klient_col"))
    grp_col = result.get("klient_col") or "Zlecenie produkcyjne"
    render_app6_summary(df_all, grp_col, tpm_thr, cm_thr, key_prefix="_post")
