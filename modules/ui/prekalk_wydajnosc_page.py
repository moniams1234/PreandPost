"""prekalk_wydajnosc_page.py — PreKalkulacja Wydajność editable page."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from modules.readers.wydajnosc_reader import (
    read_prekalk_wydajnosc, WYDAJNOSC_COLS, empty_wydajnosc_df,
)
from modules.utils.session import upload_key, store_uploaded_file
from modules.calculations.machine_costs import build_maszyny_sheet
from modules.calculations.prekalk_engine import build_prekalkulacja
from modules.utils.session import current_file
from modules.readers.orders_reader import read_prekalk_orders
from modules.readers.tektura_reader import read_prekalk_tektura
from modules.readers.material_service_reader import read_prekalk_material_service


def render() -> None:
    st.markdown("# ⚡ PreKalkulacja — Wydajność")
    st.markdown(
        '<div class="card">Tabela wydajności maszyn. '
        'Domyślnie wczytana z pliku Wydajność.xlsx.</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("pk_wydajnosc_df") is None:
        st.session_state["pk_wydajnosc_df"] = read_prekalk_wydajnosc(None) or empty_wydajnosc_df()

    col_up, col_reset = st.columns([3, 1])
    with col_up:
        uf = st.file_uploader("Upload nowego pliku Wydajność", type=["xlsx", "xls"],
                               key=upload_key("pk_wydajnosc_file"))
        store_uploaded_file("pk_wydajnosc_file", uf)
    with col_reset:
        st.write(""); st.write("")
        if st.button("↩️ Wczytaj domyślną", key="_pk_wy_reset"):
            loaded = read_prekalk_wydajnosc(None)
            st.session_state["pk_wydajnosc_df"] = loaded if loaded is not None else empty_wydajnosc_df()
            st.success("Wczytano domyślną wydajność.")
            st.rerun()

    if uf is not None:
        if st.button("📥 Wczytaj Wydajność z pliku", key="_pk_load_wy"):
            loaded = read_prekalk_wydajnosc(uf)
            if loaded is not None:
                st.session_state["pk_wydajnosc_df"] = loaded
                st.success(f"✅ Wczytano {len(loaded)} maszyn.")
                st.rerun()

    df_wy = st.session_state.get("pk_wydajnosc_df", empty_wydajnosc_df())

    with st.expander("➕ Dodaj maszynę", expanded=False):
        b1, b2, b3, b4, b5, b6 = st.columns([3, 2, 2, 2, 2, 1])
        wy_nm = b1.text_input("Nazwa maszyny", key="_pk_wy_nm")
        wy_sr = b2.number_input("Stawka rbg",   min_value=0.0, value=0.0, key="_pk_wy_sr")
        wy_su = b3.number_input("Set Up (min)", min_value=0.0, value=0.0, key="_pk_wy_su")
        wy_wy = b4.number_input("Wydajność",    min_value=0.0, value=0.0, key="_pk_wy_wy")
        wy_mi = b5.selectbox("Miara", ["ark/h", "szt/h", "ark/szt"], key="_pk_wy_mi")
        if b6.button("Dodaj", key="_pk_wy_add"):
            if wy_nm.strip():
                new_row = pd.DataFrame([{
                    "Nazwa maszyny": wy_nm.strip(), "Stawka rbg": wy_sr,
                    "Set Up czas": wy_su, "Wydajność": wy_wy, "Miara": wy_mi,
                }])
                st.session_state["pk_wydajnosc_df"] = pd.concat(
                    [df_wy, new_row], ignore_index=True
                )
                st.rerun()

    edited = st.data_editor(
        df_wy, use_container_width=True, num_rows="dynamic", key="_pk_wy_ed",
        column_config={
            "Stawka rbg":  st.column_config.NumberColumn("Stawka rbg", min_value=0.0, format="%.2f"),
            "Wydajność":   st.column_config.NumberColumn("Wydajność",  min_value=0.0, format="%.0f"),
            "Set Up czas": st.column_config.NumberColumn("Set Up (min)", min_value=0.0),
            "Miara":       st.column_config.SelectboxColumn(
                "Miara", options=["ark/h", "szt/h", "ark/szt"]
            ),
        },
    )
    if st.button("💾 Zapisz Wydajność", key="_pk_wy_save"):
        st.session_state["pk_wydajnosc_df"] = edited
        st.success("✅ Zapisano tabelę Wydajność.")

    st.markdown("---")
    if st.button("🔄 Przelicz PreKalkulację z aktualnymi ustawieniami", key="_pk_recalc_wy"):
        result = st.session_state.get("result")
        if result is None:
            st.error("❌ Brak Postkalkulacji.")
        else:
            warns: list[str] = []
            df_ord = read_prekalk_orders(current_file("pk_orders"))
            df_tek = read_prekalk_tektura(current_file("pk_tektura"))
            df_mat = read_prekalk_material_service(current_file("pk_material"))
            df_tl  = st.session_state.get("pk_tools_df")
            df_wy2 = st.session_state.get("pk_wydajnosc_df")
            with st.spinner("Przeliczanie…"):
                df_mz = build_maszyny_sheet(current_file("uf_czasy"), df_wy2)
                df_pk = build_prekalkulacja(
                    result, df_ord, df_tek, df_mat, df_tl, df_wy2, df_mz,
                    st.session_state.get("rates", {}), warns,
                )
            if df_pk is not None:
                st.session_state["pk_result"] = {
                    "df_pk": df_pk, "df_orders": df_ord, "df_tektura": df_tek,
                    "df_material": df_mat, "df_tools": df_tl,
                    "df_wydajnosc": df_wy2, "df_maszyny": df_mz,
                }
                st.success(f"✅ Przeliczono {len(df_pk):,} rekordów.")
            for w in warns:
                st.warning(w)
