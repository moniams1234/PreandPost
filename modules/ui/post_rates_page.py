"""post_rates_page.py — Stawki rbg page."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from modules.readers.czasy_reader import read_stawki
from modules.utils.session import upload_key, store_uploaded_file

DEFAULT_MACHINE_RATES: dict[str, float] = {
    "HP35K": 129.8224, "Maszyna lakierująca 2/Cyfra": 89.2784,
    "Easy-matrix 1": 117.2226, "Wyrywanie ręczne": 66.15,
    "Pakowanie": 59.535, "KBA 1_4": 113.9103, "BOBST": 155.4645,
    "Sklejarka 4": 125.0307, "ProWax": 76.4032, "HP7K": 118.1607,
    "Maszyna lakierująca 1/ Cyfra +SP": 89.2784, "Windmill 6": 79.4041,
    "Sklejarka 2": 125.0307, "Windmill 5": 79.4041, "Assembling 4": 49.65,
    "Klejenie ręczne": 108.1853, "Windmill 1": 79.4041, "Sklejarka  3": 125.0307,
    "Assembling 3": 49.65, "Sklejarka 1": 125.0307, "Assembling 1": 49.65,
    "Heidelberg CX 104": 207.4584, "Assembling 2": 49.65,
    "Hewlett Packard 1": 113.7299, "Maszyna lakierująca 4": 118.1154,
    "Gilotyna": 65.6869,
}


def render(recalculate_fn) -> None:
    st.markdown("# ⚙️ Stawki rbg")
    st.markdown(
        '<div class="card">Domyślne stawki rbg. '
        'Możesz je poprawić ręcznie, dodać nowe maszyny albo wczytać plik XLSX.</div>',
        unsafe_allow_html=True,
    )

    c_up, c_reset = st.columns([3, 1])
    with c_up:
        uf_stawki = st.file_uploader(
            "Upload pliku stawek rbg", type=["xlsx", "xls"],
            key=upload_key("uf_stawki"),
            help="Kolumny: Nazwa maszyny oraz Stawka rbg.",
        )
        store_uploaded_file("uf_stawki", uf_stawki)
    with c_reset:
        st.write(""); st.write("")
        if st.button("↩️ Przywróć domyślne", key="_reset_rates"):
            st.session_state["rates"] = DEFAULT_MACHINE_RATES.copy()
            st.session_state["settings_changed"] = True
            st.rerun()

    if uf_stawki is not None:
        loaded = read_stawki(uf_stawki)
        if loaded:
            if st.button("📥 Wczytaj stawki z pliku", key="_load_rates_file"):
                st.session_state["rates"] = loaded
                st.session_state["settings_changed"] = True
                st.success(f"✅ Wczytano {len(loaded)} stawek.")
                st.rerun()
        else:
            st.warning("Nie rozpoznano kolumn. Wymagane: Nazwa maszyny i Stawka rbg.")

    rates = dict(st.session_state.get("rates", DEFAULT_MACHINE_RATES.copy()))

    with st.expander("➕ Dodaj maszynę", expanded=False):
        c1, c2, c3 = st.columns([3, 2, 1])
        nm_new = c1.text_input("Nazwa maszyny", key="_nm_new_rates")
        rt_new = c2.number_input("Stawka rbg (PLN/h)", value=100.0, min_value=0.0,
                                  key="_rt_new_rates")
        if c3.button("Dodaj", key="_btn_add_mach_rates"):
            if nm_new.strip():
                rates[nm_new.strip()] = rt_new
                st.session_state["rates"] = rates
                st.session_state["settings_changed"] = True
                st.rerun()

    df_r = pd.DataFrame(list(rates.items()), columns=["Nazwa maszyny", "Stawka rbg (PLN/h)"])
    edited_r = st.data_editor(
        df_r, use_container_width=True, num_rows="dynamic", key="_rates_ed",
        column_config={
            "Stawka rbg (PLN/h)": st.column_config.NumberColumn(
                "Stawka rbg (PLN/h)", min_value=0.0, step=1.0, format="%.2f"
            ),
        },
    )
    if st.button("💾 Zapisz stawki rbg", key="_save_rates"):
        new_rates = dict(zip(edited_r["Nazwa maszyny"], edited_r["Stawka rbg (PLN/h)"]))
        st.session_state["rates"] = {k: v for k, v in new_rates.items() if k}
        st.session_state["settings_changed"] = True
        st.success("✅ Zapisano stawki rbg.")

    st.markdown("---")
    st.info("Po zmianie stawek kliknij Przelicz, aby zaktualizować wynik.")
    if st.button("🔄 Przelicz ponownie", key="_recalc_rates"):
        recalculate_fn(show_success=True)
