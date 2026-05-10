"""post_parameters_page.py — Parametry page."""
from __future__ import annotations

import streamlit as st


def render(recalculate_fn) -> None:
    st.markdown("# 🔧 Parametry")
    st.markdown(
        '<div class="card">Parametry globalnych obliczeń — Other costs %, progi alertów.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    other_pct = c1.number_input(
        "Other costs %",
        value=float(st.session_state.get("other_pct", 2.0)),
        min_value=0.0, max_value=100.0, step=0.5, key="_par_other",
    )
    tpm_thr = c2.number_input(
        "Próg alertu TPM % (np. 60)",
        value=float(st.session_state.get("tpm_thr", 60.0)),
        min_value=0.0, max_value=100.0, step=1.0, key="_par_tpm",
    )
    cm_thr = c3.number_input(
        "Próg alertu CM % (np. 40)",
        value=float(st.session_state.get("cm_thr", 40.0)),
        min_value=0.0, max_value=100.0, step=1.0, key="_par_cm",
    )

    if st.button("💾 Zapisz parametry", key="_save_params"):
        st.session_state["other_pct"] = other_pct
        st.session_state["tpm_thr"]   = tpm_thr
        st.session_state["cm_thr"]    = cm_thr
        st.session_state["settings_changed"] = True
        st.success("✅ Zapisano parametry.")

    st.markdown("---")
    if st.button("🔄 Przelicz ponownie", key="_recalc_params"):
        recalculate_fn(show_success=True)
