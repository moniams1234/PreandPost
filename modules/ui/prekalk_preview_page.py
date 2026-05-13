"""prekalk_preview_page.py — PreKalkulacja preview page."""
from __future__ import annotations

import streamlit as st
from modules.ui.shared import section_title, kpi_card
from modules.calculations.summaries import build_prekalk_summary
from modules.calculations.machine_costs import build_maszyny_sheet
from modules.calculations.prekalk_engine import build_prekalkulacja
from modules.readers.orders_reader import read_prekalk_orders
from modules.readers.tektura_reader import read_prekalk_tektura
from modules.readers.material_service_reader import read_prekalk_material_service
from modules.utils.session import current_file


def render() -> None:
    st.markdown("# 🔍 PreKalkulacja — Podgląd")

    pk_res = st.session_state.get("pk_result")
    if pk_res is None:
        st.warning(
            "⚠️ Brak danych. Przejdź do **PreKalkulacja – Upload** i kliknij **▶ Przelicz**."
        )
        st.stop()

    df_pk = pk_res["df_pk"]

    # ── KPIs ─────────────────────────────────────────────────────────────────
    sv  = df_pk["Sales Value"].sum()
    tpm = df_pk["TPM"].sum()
    cm  = df_pk["CM"].sum()
    tpm_pct = tpm / sv if sv else 0
    cm_pct  = cm  / sv if sv else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(kpi_card(f"{len(df_pk):,}", "Rekordów", "b"), unsafe_allow_html=True)
    k2.markdown(kpi_card(f"{sv:,.0f}", "Sales Value PLN"), unsafe_allow_html=True)
    k3.markdown(kpi_card(f"{tpm:,.0f}", "TPM PLN",
                          "g" if tpm_pct >= 0.6 else "r"), unsafe_allow_html=True)
    k4.markdown(kpi_card(f"{tpm_pct:.1%}", "TPM%",
                          "g" if tpm_pct >= 0.6 else "r"), unsafe_allow_html=True)
    k5.markdown(kpi_card(f"{cm_pct:.1%}", "CM%",
                          "g" if cm_pct >= 0.4 else "r"), unsafe_allow_html=True)

    st.markdown("---")

    # ── Recalc button ─────────────────────────────────────────────────────────
    if st.button("🔄 Przelicz ponownie", key="_pk_recalc_pv"):
        result = st.session_state.get("result")
        if result:
            warns: list[str] = []
            df_wy2 = st.session_state.get("post_wydajnosc_df")
            with st.spinner("Przeliczanie…"):
                df_ord = read_prekalk_orders(current_file("post_orders"))
                df_tek = read_prekalk_tektura(current_file("post_tektura"))
                df_mat = read_prekalk_material_service(current_file("post_material"))
                df_mz  = build_maszyny_sheet(current_file("uf_czasy"), df_wy2)
                df_pk2 = build_prekalkulacja(
                    result, df_ord, df_tek, df_mat,
                    st.session_state.get("post_tools_df"), df_wy2, df_mz,
                    st.session_state.get("rates", {}), warns,
                )
            if df_pk2 is not None:
                st.session_state["pk_result"] = {
                    "df_pk": df_pk2, "df_orders": df_ord, "df_tektura": df_tek,
                    "df_material": df_mat,
                    "df_tools": st.session_state.get("post_tools_df"),
                    "df_wydajnosc": df_wy2, "df_maszyny": df_mz,
                }
                st.success("✅ Przeliczono.")
                st.rerun()
            for w in warns:
                st.warning(w)

    # ── Table ─────────────────────────────────────────────────────────────────
    section_title("📊 Tabela PreKalkulacja")
    all_cols = list(df_pk.columns)
    KEY_COLS = ["Numer", "Klient", "Zamówienie", "Zlecenie produkcyjne",
                "Wykrojnik", "Nesting", "Liczba arkuszy", "Koszt tektury",
                "Total Materials Cost", "Total DL", "Sales Value", "TPM", "CM", "TPM%", "CM%"]
    default_show = [c for c in KEY_COLS if c in all_cols][:15]
    show_cols = st.multiselect("Kolumny do wyświetlenia", all_cols,
                                default=default_show, key="_pk_col_sel_pv")

    if show_cols:
        import pandas as pd
        fmt_map = {}
        for c in show_cols:
            if c in {"TPM%", "CM%"}:
                fmt_map[c] = "{:.1%}"
            elif any(k in c.lower() for k in ["koszt", "value", "tpm", "cm", "total", "sales"]):
                fmt_map[c] = "{:,.0f}"
        try:
            st.dataframe(
                df_pk[show_cols].style.format(fmt_map, na_rep="–"),
                use_container_width=True, height=480,
            )
        except Exception:
            st.dataframe(df_pk[show_cols], use_container_width=True, height=480)

    # ── Monthly summary ───────────────────────────────────────────────────────
    section_title("📅 Podsumowanie miesięczne")
    df_sum = build_prekalk_summary(df_pk)
    if not df_sum.empty:
        try:
            st.dataframe(
                df_sum.style.format({
                    "Sales Value": "{:,.0f}", "TPM": "{:,.0f}", "CM": "{:,.0f}",
                    "TPM%": "{:.1%}", "CM%": "{:.1%}",
                }),
                use_container_width=True,
            )
        except Exception:
            st.dataframe(df_sum, use_container_width=True)

    # ── Maszyny preview ───────────────────────────────────────────────────────
    df_mz = pk_res.get("df_maszyny")
    if df_mz is not None and not df_mz.empty:
        with st.expander("🏭 Arkusz maszyny (podgląd 100 wierszy)", expanded=False):
            st.dataframe(df_mz.head(100), use_container_width=True)
