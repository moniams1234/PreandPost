"""post_click_costs_page.py — Koszty klików page."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from modules.calculations.profitability_engine import read_click_costs
from modules.utils.session import upload_key, store_uploaded_file

DEFAULT_CLICK_COSTS: dict[str, dict[str, float]] = {
    "HP Indigo 7K Digital Press": {
        "Yellow": .05, "Magenta": .05, "Cyan": .05,
        "Black": .05, "Violet": .06, "Orange": .06, "default": .05,
    },
    "HP Indigo 35K Digital Press": {
        "Yellow": .04, "Magenta": .04, "Cyan": .04,
        "Black": .04, "Violet": .05, "Orange": .05, "default": .04,
    },
}


def render(recalculate_fn) -> None:
    st.markdown("# 🖨️ Koszty klików")
    st.markdown(
        '<div class="card">Koszty per separacja per maszyna i kolor.</div>',
        unsafe_allow_html=True,
    )

    uf_cc = st.file_uploader("Upload pliku kosztów klików", type=["xlsx", "xls"],
                               key=upload_key("uf_click_costs"))
    store_uploaded_file("uf_click_costs", uf_cc)

    if uf_cc is not None:
        loaded = read_click_costs(uf_cc)
        if loaded:
            if st.button("📥 Wczytaj koszty klików z pliku", key="_load_cc_file"):
                st.session_state["click_costs"] = loaded
                st.session_state["settings_changed"] = True
                st.success(f"✅ Wczytano {len(loaded)} maszyn.")
                st.rerun()
        else:
            st.warning("Nie rozpoznano kolumn w pliku kosztów klików.")

    click_costs = st.session_state.get("click_costs", DEFAULT_CLICK_COSTS.copy())

    cc_rows = [
        {"Maszyna": k, "Kolor": c, "Koszt PLN/sep": v}
        for k, colors in click_costs.items()
        for c, v in colors.items()
    ]
    df_cc = (pd.DataFrame(cc_rows) if cc_rows
              else pd.DataFrame(columns=["Maszyna", "Kolor", "Koszt PLN/sep"]))
    edited_cc = st.data_editor(
        df_cc, use_container_width=True, num_rows="dynamic", key="_cc_ed",
        column_config={
            "Koszt PLN/sep": st.column_config.NumberColumn(
                "Koszt PLN/sep", min_value=0.0, step=0.01, format="%.4f"
            ),
        },
    )
    if st.button("💾 Zapisz koszty klików", key="_save_cc"):
        new_cc: dict[str, dict[str, float]] = {}
        for _, row in edited_cc.iterrows():
            mach = str(row.get("Maszyna", "")).strip()
            color = str(row.get("Kolor", "")).strip()
            cost = float(row.get("Koszt PLN/sep", 0) or 0)
            if mach:
                new_cc.setdefault(mach, {})[color] = cost
        st.session_state["click_costs"] = new_cc
        st.session_state["settings_changed"] = True
        st.success("✅ Zapisano koszty klików.")

    st.markdown("---")
    if st.button("🔄 Przelicz ponownie", key="_recalc_cc"):
        recalculate_fn(show_success=True)
