"""prekalk_tools_page.py — PreKalkulacja Tools editable page."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from modules.readers.tools_reader import read_prekalk_tools, TOOLS_COLS, empty_tools_df
from modules.utils.session import upload_key, store_uploaded_file


def render() -> None:
    st.markdown("# 🔩 PreKalkulacja — Tools")
    st.markdown(
        '<div class="card">Tabela narzędzi (wykrojników) do wyznaczenia Nestingu. '
        'Domyślnie wczytana z pliku tool_list.</div>',
        unsafe_allow_html=True,
    )

    # Auto-load defaults on first visit.
    # Do NOT use "df or empty_df" with pandas DataFrame, because DataFrame truth value is ambiguous.
    if st.session_state.get("pk_tools_df") is None:
        loaded_defaults = read_prekalk_tools(None)
        st.session_state["pk_tools_df"] = loaded_defaults if loaded_defaults is not None else empty_tools_df()
        if loaded_defaults is not None and not loaded_defaults.empty:
            st.success(f"✅ Wczytano domyślne Tools: {len(loaded_defaults)} rekordów.")
        else:
            st.warning("⚠️ Nie znaleziono lub nie rozpoznano domyślnego pliku data/default_tools.xlsx.")

    col_up, col_reset = st.columns([3, 1])
    with col_up:
        uf = st.file_uploader("Upload nowego pliku Tools", type=["xlsx", "xls"],
                               key=upload_key("pk_tools_file"))
        store_uploaded_file("pk_tools_file", uf)
    with col_reset:
        st.write(""); st.write("")
        if st.button("↩️ Wczytaj domyślny", key="_pk_tl_reset"):
            loaded = read_prekalk_tools(None)
            st.session_state["pk_tools_df"] = loaded if loaded is not None else empty_tools_df()
            st.success("Wczytano domyślny plik tools.")
            st.rerun()

    if uf is not None:
        if st.button("📥 Wczytaj Tools z pliku", key="_pk_load_tl"):
            loaded = read_prekalk_tools(uf)
            if loaded is not None:
                st.session_state["pk_tools_df"] = loaded
                st.success(f"✅ Wczytano {len(loaded)} narzędzi.")
                st.rerun()

    df_tl = st.session_state.get("pk_tools_df", empty_tools_df())

    with st.expander("➕ Dodaj nowe narzędzie", expanded=False):
        a1, a2, a3, a4, a5 = st.columns([3, 2, 2, 2, 1])
        nm_new = a1.text_input("Nazwa narzędzia",  key="_pk_tl_nm")
        tp_new = a2.text_input("Typ narzędzia",    key="_pk_tl_tp")
        kl_new = a3.text_input("Klient",            key="_pk_tl_kl")
        ne_new = a4.number_input("Nesting", min_value=0.0, value=1.0, step=1.0,
                                  key="_pk_tl_ne")
        if a5.button("Dodaj", key="_pk_tl_add"):
            if nm_new.strip():
                new_row = pd.DataFrame([{
                    "Nazwa narzędzia": nm_new.strip(),
                    "Typ narzędzia":   tp_new.strip(),
                    "Klient":          kl_new.strip(),
                    "Ilość użytków wykrojnika / Nesting": ne_new,
                }])
                st.session_state["pk_tools_df"] = pd.concat(
                    [df_tl, new_row], ignore_index=True
                )
                st.rerun()

    edited = st.data_editor(
        df_tl, use_container_width=True, num_rows="dynamic", key="_pk_tl_ed",
        column_config={
            "Ilość użytków wykrojnika / Nesting": st.column_config.NumberColumn(
                "Nesting", min_value=0.0, step=1.0
            ),
        },
    )
    if st.button("💾 Zapisz tabelę Tools", key="_pk_tl_save"):
        st.session_state["pk_tools_df"] = edited
        st.success("✅ Zapisano tabelę Tools.")
