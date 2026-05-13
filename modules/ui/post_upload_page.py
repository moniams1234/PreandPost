"""post_upload_page.py — PostKalkulacja Upload page."""
from __future__ import annotations

import streamlit as st
from modules.utils.session import upload_key, store_uploaded_file, current_file
from modules.ui.shared import section_title, badge


def render(recalculate_fn) -> None:
    st.markdown("# 📂 Upload plików")
    st.markdown(
        '<div class="card">Uploaduj pliki źródłowe. '
        '<strong>Baza (post_list)</strong> jest wymagana — reszta jest opcjonalna. '
        'Po załadowaniu plików kliknij <strong>▶ Oblicz</strong>.</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📋 Wymagane")
        uf = st.file_uploader("Baza / post_list ⭐", type=["xlsx", "xls"],
                               key=upload_key("uf_base"))
        store_uploaded_file("uf_base", uf)

        st.markdown("#### 🏭 Produkcja & Faktury")
        uf = st.file_uploader("Czasy dla aplikacji", type=["xlsx", "xls"],
                               key=upload_key("uf_czasy"))
        store_uploaded_file("uf_czasy", uf)

        uf = st.file_uploader("Zlecenia + faktury", type=["xlsx", "xls"],
                               key=upload_key("uf_zlec"))
        store_uploaded_file("uf_zlec", uf)

        uf = st.file_uploader("Faktury – linie", type=["xlsx", "xls"],
                               key=upload_key("uf_fry"))
        store_uploaded_file("uf_fry", uf)

    with col2:
        st.markdown("#### 💰 Koszty")
        uf = st.file_uploader("Kliki / Inks", type=["xlsx", "xls"],
                               key=upload_key("uf_inks"))
        store_uploaded_file("uf_inks", uf)

        uf = st.file_uploader("Farby podsumowanie (Offset)", type=["xlsx", "xls"],
                               key=upload_key("uf_farby"))
        store_uploaded_file("uf_farby", uf)

        st.caption("Stawki rbg i koszty klików można uploadować w dedykowanych zakładkach.")

    # ── New PostKalkulacja supplementary files ────────────────────────────────
    st.markdown("---")
    st.markdown("#### ✂️ Dane Gilotyny & Tektury (Postkalkulacja)")
    st.markdown(
        '<div class="card">Pliki do obliczenia kosztu gilotyny i nestingu w Profitability. '
        'Wszystkie trzy są opcjonalne — dostarczają kolumny: liczba cięć, Format, Die cut, Nesting, koszt gilotyny.</div>',
        unsafe_allow_html=True,
    )

    col3, col4, col5 = st.columns(3)
    with col3:
        uf = st.file_uploader(
            "Usługa na surowcu ✂️",
            type=["xlsx", "xls"],
            key=upload_key("post_material"),
            help="Plik z kolumną Surowiec zawierającą [mindex] i N×M (liczba cięć).",
        )
        store_uploaded_file("post_material", uf)

    with col4:
        uf = st.file_uploader(
            "Orders 📋",
            type=["xlsx", "xls"],
            key=upload_key("post_orders"),
            help="Plik Orders z kolumnami: Numer-Linia, Wykrojnik, Format, Klient.",
        )
        store_uploaded_file("post_orders", uf)

    with col5:
        uf = st.file_uploader(
            "Tektura 🌿",
            type=["xlsx", "xls", "csv"],
            key=upload_key("post_tektura"),
            help="Plik Tektura z kolumnami: job_name, mindex.",
        )
        store_uploaded_file("post_tektura", uf)

    # Status grid
    st.markdown("---")
    section_title("📁 Status plików")
    FILES_STATUS = [
        ("Baza", "uf_base"), ("Czasy", "uf_czasy"),
        ("Zlecenia+FV", "uf_zlec"), ("Faktury linie", "uf_fry"),
        ("Kliki/Inks", "uf_inks"), ("Stawki rbg", "rates"),
        ("Farby", "uf_farby"),
        ("Usługa na surowcu", "post_material"),
        ("Orders", "post_orders"),
        ("Tektura", "post_tektura"),
    ]
    sc = st.columns(4)
    for i, (label, key) in enumerate(FILES_STATUS):
        if key.startswith(("uf_", "post_")):
            ok = current_file(key) is not None
        else:
            ok = st.session_state.get(key) is not None
        sc[i % 4].markdown(f"**{label}** {badge(ok)}", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### ▶ Uruchom obliczenia")
    st.markdown(
        "Po kliknięciu aplikacja przetworzy wszystkie załadowane pliki "
        "i zapisze wynik w pamięci sesji."
    )
    if st.button("▶ Oblicz Profitability", use_container_width=False,
                 key="_post_calc_btn"):
        recalculate_fn(show_success=True)
    st.markdown("</div>", unsafe_allow_html=True)
