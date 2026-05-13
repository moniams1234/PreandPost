"""post_wydajnosc_page.py — PostKalkulacja Wydajność editable page (mirrored from PreKalkulacja)."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from modules.readers.wydajnosc_reader import (
    read_prekalk_wydajnosc, WYDAJNOSC_COLS, empty_wydajnosc_df,
)
from modules.utils.session import upload_key, store_uploaded_file


def render(recalculate_fn=None) -> None:
    st.markdown("# ⚡ Postkalkulacja — Wydajność")
    st.markdown(
        '<div class="card">Tabela wydajności maszyn używana do obliczania kosztu gilotyny '
        'w kolumnach Profitability. Domyślnie wczytana z pliku Wydajność.xlsx.</div>',
        unsafe_allow_html=True,
    )

    # Auto-load defaults on first visit.
    if st.session_state.get("post_wydajnosc_df") is None:
        loaded_defaults = read_prekalk_wydajnosc(None)
        st.session_state["post_wydajnosc_df"] = loaded_defaults if loaded_defaults is not None else empty_wydajnosc_df()
        if loaded_defaults is not None and not loaded_defaults.empty:
            st.success(f"✅ Wczytano domyślną Wydajność: {len(loaded_defaults)} rekordów.")
        else:
            st.warning("⚠️ Nie znaleziono lub nie rozpoznano domyślnego pliku data/default_wydajnosc.xlsx.")

    col_up, col_reset = st.columns([3, 1])
    with col_up:
        uf = st.file_uploader("Upload nowego pliku Wydajność", type=["xlsx", "xls"],
                               key=upload_key("post_wydajnosc_file"))
        store_uploaded_file("post_wydajnosc_file", uf)
    with col_reset:
        st.write(""); st.write("")
        if st.button("↩️ Wczytaj domyślną", key="_post_wy_reset"):
            loaded = read_prekalk_wydajnosc(None)
            st.session_state["post_wydajnosc_df"] = loaded if loaded is not None else empty_wydajnosc_df()
            st.success("Wczytano domyślną wydajność.")
            st.rerun()

    if uf is not None:
        if st.button("📥 Wczytaj Wydajność z pliku", key="_post_load_wy"):
            loaded = read_prekalk_wydajnosc(uf)
            if loaded is not None:
                st.session_state["post_wydajnosc_df"] = loaded
                st.success(f"✅ Wczytano {len(loaded)} maszyn.")
                st.rerun()

    df_wy = st.session_state.get("post_wydajnosc_df", empty_wydajnosc_df())

    with st.expander("➕ Dodaj maszynę", expanded=False):
        b1, b2, b3, b4, b5, b6 = st.columns([3, 2, 2, 2, 2, 1])
        wy_nm = b1.text_input("Nazwa maszyny", key="_post_wy_nm")
        wy_sr = b2.number_input("Stawka rbg",   min_value=0.0, value=0.0, key="_post_wy_sr")
        wy_su = b3.number_input("Set Up (min)", min_value=0.0, value=0.0, key="_post_wy_su")
        wy_wy = b4.number_input("Wydajność",    min_value=0.0, value=0.0, key="_post_wy_wy")
        wy_mi = b5.selectbox("Miara", ["ark/h", "szt/h", "ark/szt"], key="_post_wy_mi")
        if b6.button("Dodaj", key="_post_wy_add"):
            if wy_nm.strip():
                new_row = pd.DataFrame([{
                    "Nazwa maszyny": wy_nm.strip(), "Stawka rbg": wy_sr,
                    "Set Up czas": wy_su, "Wydajność": wy_wy, "Miara": wy_mi,
                }])
                st.session_state["post_wydajnosc_df"] = pd.concat(
                    [df_wy, new_row], ignore_index=True
                )
                st.rerun()

    edited = st.data_editor(
        df_wy, use_container_width=True, num_rows="dynamic", key="_post_wy_ed",
        column_config={
            "Stawka rbg":  st.column_config.NumberColumn("Stawka rbg", min_value=0.0, format="%.2f"),
            "Wydajność":   st.column_config.NumberColumn("Wydajność",  min_value=0.0, format="%.0f"),
            "Set Up czas": st.column_config.NumberColumn("Set Up (min)", min_value=0.0),
            "Miara":       st.column_config.SelectboxColumn(
                "Miara", options=["ark/h", "szt/h", "ark/szt"]
            ),
        },
    )
    if st.button("💾 Zapisz Wydajność", key="_post_wy_save"):
        st.session_state["post_wydajnosc_df"] = edited
        st.success("✅ Zapisano tabelę Wydajność.")

    if st.button("🔄 Przelicz Profitability po zmianie Wydajności", key="_post_recalc_after_wydajnosc"):
        st.session_state["post_wydajnosc_df"] = edited
        if recalculate_fn:
            recalculate_fn(show_success=True)
        else:
            st.info("Przejdź do Upload plików i kliknij Oblicz Profitability.")

    st.markdown("---")
    st.info(
        "💡 Po zmianie Wydajności kliknij **▶ Oblicz Profitability** "
        "na stronie Upload, aby przeliczyć koszt gilotyny."
    )
