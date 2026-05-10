"""prekalk_summary_page.py — PreKalkulacja Podsumowanie in app(6) layout."""
from __future__ import annotations

import streamlit as st

from modules.ui.app6_views import render_app6_summary, find_client_col


def render() -> None:
    st.markdown("# 📈 PreKalkulacja — Podsumowanie")

    pk_res = st.session_state.get("pk_result")
    if pk_res is None:
        st.warning("⚠️ Brak danych. Przejdź do **PreKalkulacja – Upload** i przelicz.")
        st.stop()

    df_pk = pk_res["df_pk"]
    tpm_thr = st.session_state.get("tpm_thr", 60.0)
    cm_thr = st.session_state.get("cm_thr", 40.0)
    grp_col = find_client_col(df_pk, "Klient" if "Klient" in df_pk.columns else None)

    render_app6_summary(df_pk, grp_col, tpm_thr, cm_thr, key_prefix="_pk")
