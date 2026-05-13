"""prekalk_upload_page.py — PreKalkulacja Upload page."""
from __future__ import annotations

import streamlit as st
from modules.utils.session import upload_key, store_uploaded_file, current_file
from modules.ui.shared import section_title, badge
from modules.readers.orders_reader import read_prekalk_orders
from modules.readers.tektura_reader import read_prekalk_tektura
from modules.readers.material_service_reader import read_prekalk_material_service
from modules.calculations.machine_costs import build_maszyny_sheet
from modules.calculations.prekalk_engine import build_prekalkulacja


def _run_calculation(result, rates, warns):
    # Use post_* keys (Orders, Tektura, Material moved to PostKalkulacja)
    df_ord = read_prekalk_orders(current_file("post_orders"))
    df_tek = read_prekalk_tektura(current_file("post_tektura"))
    df_mat = read_prekalk_material_service(current_file("post_material"))
    df_tl  = st.session_state.get("post_tools_df")
    df_wy  = st.session_state.get("post_wydajnosc_df")
    df_mz  = build_maszyny_sheet(current_file("uf_czasy"), df_wy)
    df_pk  = build_prekalkulacja(result, df_ord, df_tek, df_mat, df_tl, df_wy, df_mz,
                                  rates, warns)
    if df_pk is not None:
        st.session_state["pk_result"] = {
            "df_pk": df_pk, "df_orders": df_ord, "df_tektura": df_tek,
            "df_material": df_mat, "df_tools": df_tl,
            "df_wydajnosc": df_wy, "df_maszyny": df_mz,
        }
    return df_pk


def render() -> None:
    st.markdown("# 📦 PreKalkulacja — Upload plików")
    st.markdown(
        '<div class="card">PreKalkulacja korzysta z plików załadowanych w <strong>Postkalkulacja → Upload plików</strong>: '
        'Orders, Tektura, Usługa na surowcu, Tools i Wydajność. '
        'Postkalkulacja musi być obliczona wcześniej.</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "📋 **Pliki Orders, Tektura, Usługa na surowcu, Tools i Wydajność** "
        "zarządzane są w sekcji **Postkalkulacja** (Upload plików, Tools, Wydajność). "
        "Nie ma potrzeby ich ponownego uploadowania tutaj."
    )

    # Status grid
    st.markdown("---")
    section_title("📁 Status plików PreKalkulacji")
    STATUS = [
        ("Orders",         "post_orders"),
        ("Tektura",        "post_tektura"),
        ("Materiał",       "post_material"),
        ("Tools",          None),
        ("Wydajność",      None),
        ("Postkalkulacja", None),
    ]
    sc = st.columns(3)
    for i, (label, key) in enumerate(STATUS):
        if key:
            ok = current_file(key) is not None
        elif label == "Tools":
            ok = st.session_state.get("post_tools_df") is not None
        elif label == "Wydajność":
            ok = st.session_state.get("post_wydajnosc_df") is not None
        else:
            ok = st.session_state.get("result") is not None
        sc[i % 3].markdown(f"**{label}** {badge(ok)}", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### ▶ Przelicz PreKalkulację")
    if st.button("▶ Przelicz PreKalkulację", key="_pk_calc_upload"):
        result = st.session_state.get("result")
        if result is None:
            st.error("❌ Najpierw oblicz Postkalkulację.")
        else:
            rates = st.session_state.get("rates", {})
            warns_pk: list[str] = []
            with st.spinner("Wczytywanie i łączenie danych…"):
                df_pk = _run_calculation(result, rates, warns_pk)
            if df_pk is not None:
                st.success(f"✅ PreKalkulacja obliczona — {len(df_pk):,} rekordów.")
            for w in warns_pk:
                st.warning(w)
    st.markdown("</div>", unsafe_allow_html=True)

