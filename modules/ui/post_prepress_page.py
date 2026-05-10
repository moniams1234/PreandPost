"""post_prepress_page.py — Prepress page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

DEFAULT_PREPRESS_CLIENTS: dict[str, dict[str, float]] = {
    "Oticon A/S / DGS Denmark": {"digital": 10.0, "offset": 40.0},
    "Abacus Medicine A/S":       {"digital": 10.0, "offset": 40.0},
    "Kohlpharma GmbH":           {"digital": 10.0, "offset": 40.0},
    "Roche":                     {"digital": 10.0, "offset": 40.0},
}
DEFAULT_PP_DIGITAL: float = 10.0
DEFAULT_PP_OFFSET: float  = 40.0


def render(recalculate_fn) -> None:
    st.markdown("# 🎨 Prepress")
    st.markdown(
        '<div class="card">Stawki Prepress Digital / Offset per klient.</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    pp_digital = c1.number_input(
        "Domyślna stawka Digital (PLN/zamówienie)",
        value=float(st.session_state.get("pp_digital", DEFAULT_PP_DIGITAL)),
        min_value=0.0, step=1.0, key="_pp_digi",
    )
    pp_offset = c2.number_input(
        "Domyślna stawka Offset (PLN/zamówienie)",
        value=float(st.session_state.get("pp_offset", DEFAULT_PP_OFFSET)),
        min_value=0.0, step=1.0, key="_pp_offs",
    )
    if st.button("💾 Zapisz domyślne stawki Prepress", key="_save_pp_default"):
        st.session_state["pp_digital"] = pp_digital
        st.session_state["pp_offset"]  = pp_offset
        st.session_state["settings_changed"] = True
        st.success("✅ Zapisano domyślne stawki Prepress.")

    st.markdown("---")
    prepress = st.session_state.get("prepress", DEFAULT_PREPRESS_CLIENTS.copy())
    pp_rows = [{"Klient": k, "Digital": v["digital"], "Offset": v["offset"]}
               for k, v in prepress.items()]
    df_pp = (pd.DataFrame(pp_rows) if pp_rows
              else pd.DataFrame(columns=["Klient", "Digital", "Offset"]))
    edited_pp = st.data_editor(
        df_pp, use_container_width=True, num_rows="dynamic", key="_pp_ed",
        column_config={
            "Digital": st.column_config.NumberColumn("Digital", min_value=0.0, format="%.2f"),
            "Offset":  st.column_config.NumberColumn("Offset",  min_value=0.0, format="%.2f"),
        },
    )
    if st.button("💾 Zapisz Prepress per klient", key="_save_pp"):
        new_pp: dict[str, dict[str, float]] = {}
        for _, row in edited_pp.iterrows():
            kl = str(row.get("Klient", "")).strip()
            if kl:
                new_pp[kl] = {
                    "digital": float(row.get("Digital", 0) or 0),
                    "offset":  float(row.get("Offset",  0) or 0),
                }
        st.session_state["prepress"] = new_pp
        st.session_state["settings_changed"] = True
        st.success("✅ Zapisano stawki Prepress.")

    st.markdown("---")
    if st.button("🔄 Przelicz ponownie", key="_recalc_pp"):
        recalculate_fn(show_success=True)
