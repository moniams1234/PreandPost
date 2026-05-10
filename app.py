"""
╔═══════════════════════════════════════════════════════════════════╗
║  Postkalkulacja + PreKalkulacja Profitability  —  app.py          ║
║  Production-grade Streamlit financial dashboard                   ║
╚═══════════════════════════════════════════════════════════════════╝

Run:
    streamlit run app.py
"""

from __future__ import annotations

import warnings
from typing import Any

import streamlit as st

warnings.filterwarnings("ignore")

# ════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG  (must be the FIRST Streamlit call)
# ════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Postkalkulacja & PreKalkulacja",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════════════════
#  MODULE IMPORTS  (after set_page_config)
# ════════════════════════════════════════════════════════════════════════════

from modules.ui.shared import inject_css
from modules.utils.session import upload_key, store_uploaded_file, current_file
from modules.calculations.profitability_engine import build_profitability
from modules.ui.post_rates_page import DEFAULT_MACHINE_RATES
from modules.ui.post_click_costs_page import DEFAULT_CLICK_COSTS
from modules.ui.post_prepress_page import DEFAULT_PREPRESS_CLIENTS, DEFAULT_PP_DIGITAL, DEFAULT_PP_OFFSET

# ════════════════════════════════════════════════════════════════════════════
#  INJECT CSS
# ════════════════════════════════════════════════════════════════════════════

inject_css()

# ════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INITIALISATION
# ════════════════════════════════════════════════════════════════════════════

_SS_DEFAULTS: dict[str, Any] = {
    # PostKalkulacja
    "rates":              DEFAULT_MACHINE_RATES.copy(),
    "rates_loaded":       True,
    "click_costs":        {k: v.copy() for k, v in DEFAULT_CLICK_COSTS.items()},
    "prepress":           {k: v.copy() for k, v in DEFAULT_PREPRESS_CLIENTS.items()},
    "pp_digital":         DEFAULT_PP_DIGITAL,
    "pp_offset":          DEFAULT_PP_OFFSET,
    "other_pct":          2.0,
    "tpm_thr":            60.0,
    "cm_thr":             40.0,
    "result":             None,
    "settings_changed":   False,
    "upload_clear_nonce": 0,
    # PreKalkulacja
    "pk_result":          None,
    "pk_tools_df":        None,
    "pk_wydajnosc_df":    None,
    # Navigation
    "active_module":      "PostKalkulacja",
    "post_page":          "📂 Upload plików",
    "pk_page":            "📦 Upload",
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ════════════════════════════════════════════════════════════════════════════
#  RECALCULATE HELPER
# ════════════════════════════════════════════════════════════════════════════

def recalculate_profitability(show_success: bool = True) -> bool:
    if not current_file("uf_base"):
        st.error("❌ Brak pliku Baza! Załaduj w zakładce Upload plików.")
        return False
    with st.spinner("Przeliczanie profitability…"):
        result, warns = build_profitability(
            current_file("uf_base"),
            current_file("uf_czasy"),
            current_file("uf_zlec"),
            current_file("uf_fry"),
            current_file("uf_inks"),
            current_file("uf_farby"),
            st.session_state.get("rates", {}),
            st.session_state.get("click_costs", {}),
            st.session_state.get("prepress", {}),
            st.session_state.get("pp_digital", DEFAULT_PP_DIGITAL),
            st.session_state.get("pp_offset",  DEFAULT_PP_OFFSET),
            st.session_state.get("other_pct",  2.0),
        )
    if result:
        st.session_state["result"] = result
        st.session_state["settings_changed"] = False
        df = result["df_prof"]
        if show_success:
            sv_sum = df["Sales Value"].sum() if "Sales Value" in df.columns else 0
            st.success(
                f"✅ Przeliczono {len(df):,} rekordów · "
                f"Sprzedaż: {sv_sum:,.0f} PLN · "
                f"Miesięcy: {df['Miesiąc faktury'].nunique() if 'Miesiąc faktury' in df.columns else 0}"
            )
        for w in warns:
            st.warning(w)
        return True
    for w in warns:
        st.error(w)
    return False


def clear_all_inputs() -> None:
    POST_UPLOAD_KEYS = [
        "uf_base", "uf_czasy", "uf_zlec", "uf_fry",
        "uf_inks", "uf_farby", "uf_stawki", "uf_click_costs",
    ]
    PK_UPLOAD_KEYS = [
        "pk_orders", "pk_tektura", "pk_material",
        "pk_tools_file", "pk_wydajnosc_file",
    ]
    all_bases = POST_UPLOAD_KEYS + PK_UPLOAD_KEYS
    st.session_state["upload_clear_nonce"] = st.session_state.get("upload_clear_nonce", 0) + 1
    for key in list(st.session_state.keys()):
        if any(
            key == base or key.startswith(f"{base}_") or key == f"stored_{base}"
            for base in all_bases
        ):
            st.session_state.pop(key, None)
    # Reset calculated results and settings
    for key in ["result", "pk_result", "pk_tools_df", "pk_wydajnosc_df", "settings_changed"]:
        st.session_state[key] = None if key != "settings_changed" else False
    st.session_state["rates"]       = DEFAULT_MACHINE_RATES.copy()
    st.session_state["click_costs"] = {k: v.copy() for k, v in DEFAULT_CLICK_COSTS.items()}
    st.session_state["prepress"]    = {k: v.copy() for k, v in DEFAULT_PREPRESS_CLIENTS.items()}
    st.session_state["pp_digital"]  = DEFAULT_PP_DIGITAL
    st.session_state["pp_offset"]   = DEFAULT_PP_OFFSET
    st.session_state["other_pct"]   = 2.0
    st.session_state["tpm_thr"]     = 60.0
    st.session_state["cm_thr"]      = 40.0


# ════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

POST_PAGES = [
    "📂 Upload plików",
    "⚙️ Stawki rbg",
    "🖨️ Koszty klików",
    "🎨 Prepress",
    "🔧 Parametry",
    "📋 Podgląd Profitability",
    "📈 Podsumowanie",
    "🎯 Kokpit",
    "⬇️ Pobierz XLSX",
]

PK_PAGES = [
    "📦 Upload",
    "🔩 Tools",
    "⚡ Wydajność",
    "🔍 Podgląd",
    "📊 Podsumowanie",
    "🎯 Kokpit",
    "💾 Pobierz XLSX",
]

with st.sidebar:
    # ── Logo ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:18px 12px 8px;text-align:center;">
        <div style="font-size:2rem;margin-bottom:2px;">📊</div>
        <div style="color:#FF8C66;font-size:1.05rem;font-weight:800;letter-spacing:.04em;">
            KALKULACJA
        </div>
        <div style="color:rgba(245,217,208,.55);font-size:.70rem;letter-spacing:.08em;">
            PROFITABILITY APP
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<hr style='border-color:rgba(255,255,255,.10);margin:6px 0 10px;'>",
        unsafe_allow_html=True,
    )

    # ── Module selector ───────────────────────────────────────────────────────
    st.markdown(
        "<div style='color:rgba(245,217,208,.55);font-size:.68rem;"
        "text-transform:uppercase;letter-spacing:.1em;padding:0 4px 6px;'>MODUŁ</div>",
        unsafe_allow_html=True,
    )
    active_module = st.radio(
        "Moduł",
        ["PostKalkulacja", "PreKalkulacja"],
        index=0 if st.session_state.get("active_module", "PostKalkulacja") == "PostKalkulacja" else 1,
        key="_module_selector",
        label_visibility="hidden",
    )
    st.session_state["active_module"] = active_module

    st.markdown(
        "<hr style='border-color:rgba(255,255,255,.10);margin:10px 0;'>",
        unsafe_allow_html=True,
    )

    # ── Page selector (context-sensitive) ────────────────────────────────────
    if active_module == "PostKalkulacja":
        st.markdown(
            "<div style='color:rgba(245,217,208,.55);font-size:.68rem;"
            "text-transform:uppercase;letter-spacing:.1em;padding:0 4px 6px;'>"
            "POSTKALKULACJA</div>",
            unsafe_allow_html=True,
        )
        current_post_idx = (
            POST_PAGES.index(st.session_state.get("post_page", POST_PAGES[0]))
            if st.session_state.get("post_page") in POST_PAGES
            else 0
        )
        page = st.radio(
            "Strona PostKalkulacja",
            POST_PAGES,
            index=current_post_idx,
            key="_post_page_nav",
            label_visibility="hidden",
        )
        st.session_state["post_page"] = page
    else:
        st.markdown(
            "<div style='color:rgba(245,217,208,.55);font-size:.68rem;"
            "text-transform:uppercase;letter-spacing:.1em;padding:0 4px 6px;'>"
            "PREKALKULACJA</div>",
            unsafe_allow_html=True,
        )
        current_pk_idx = (
            PK_PAGES.index(st.session_state.get("pk_page", PK_PAGES[0]))
            if st.session_state.get("pk_page") in PK_PAGES
            else 0
        )
        page = st.radio(
            "Strona PreKalkulacja",
            PK_PAGES,
            index=current_pk_idx,
            key="_pk_page_nav",
            label_visibility="hidden",
        )
        st.session_state["pk_page"] = page

    st.markdown(
        "<hr style='border-color:rgba(255,255,255,.10);margin:14px 0 10px;'>",
        unsafe_allow_html=True,
    )

    # ── Clear button ──────────────────────────────────────────────────────────
    if st.button("🧹 Wyczyść wszystko", key="_clear_all", use_container_width=True):
        clear_all_inputs()
        st.success("Wyczyszczono dane.")
        st.rerun()
    st.caption("Czyści pliki, dane i ustawienia obu modułów.")

    st.markdown(
        "<hr style='border-color:rgba(255,255,255,.10);margin:14px 0 10px;'>",
        unsafe_allow_html=True,
    )

    # ── Status panel ──────────────────────────────────────────────────────────
    base_ok    = current_file("uf_base") is not None
    result_ok  = st.session_state.get("result") is not None
    pk_ok      = st.session_state.get("pk_result") is not None

    def _status_row(icon, label, ok, ok_txt="OK", nok_txt="brak"):
        color = "#0FA958" if ok else ("#FF5A1F" if label == "Dane" else "#C91818")
        icon2 = "✓" if ok else ("⏳" if label == "Dane" else "✗")
        txt   = ok_txt if ok else nok_txt
        return (
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:4px 0;border-bottom:1px solid rgba(255,255,255,.06);'>"
            f"<span style='color:rgba(245,217,208,.75);font-size:.78rem;'>{icon} {label}</span>"
            f"<span style='background:{color};color:#fff;border-radius:12px;"
            f"padding:2px 8px;font-size:.68rem;font-weight:700;'>{icon2} {txt}</span>"
            f"</div>"
        )

    st.markdown(
        "<div style='padding:10px 12px;background:rgba(0,0,0,.20);border-radius:10px;margin:0 4px;'>"
        "<div style='font-size:.64rem;text-transform:uppercase;letter-spacing:.08em;"
        "color:rgba(245,217,208,.50);margin-bottom:8px;'>Status sesji</div>"
        + _status_row("📋", "Baza", base_ok, "wczytana", "brak")
        + _status_row("📈", "Post dane", result_ok, "obliczone", "nie obliczone")
        + _status_row("📦", "PreKalk", pk_ok, "obliczona", "nie obliczona")
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center;color:rgba(245,217,208,.30);font-size:.65rem;"
        "letter-spacing:.05em;'>v4.0 · © Postkalkulacja & PreKalkulacja</div>",
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTING
# ════════════════════════════════════════════════════════════════════════════

tpm_thr = float(st.session_state.get("tpm_thr", 60.0))
cm_thr  = float(st.session_state.get("cm_thr",  40.0))
result  = st.session_state.get("result")

if active_module == "PostKalkulacja":
    # ── PostKalkulacja pages ──────────────────────────────────────────────────
    if page == POST_PAGES[0]:
        from modules.ui.post_upload_page import render as render_upload
        render_upload(recalculate_profitability)

    elif page == POST_PAGES[1]:
        from modules.ui.post_rates_page import render as render_rates
        render_rates(recalculate_profitability)

    elif page == POST_PAGES[2]:
        from modules.ui.post_click_costs_page import render as render_cc
        render_cc(recalculate_profitability)

    elif page == POST_PAGES[3]:
        from modules.ui.post_prepress_page import render as render_pp
        render_pp(recalculate_profitability)

    elif page == POST_PAGES[4]:
        from modules.ui.post_parameters_page import render as render_params
        render_params(recalculate_profitability)

    elif page == POST_PAGES[5]:
        from modules.ui.post_profitability_preview import render as render_pv
        render_pv(result, tpm_thr, cm_thr)

    elif page == POST_PAGES[6]:
        from modules.ui.post_summary_page import render as render_sum
        render_sum(result, tpm_thr, cm_thr)

    elif page == POST_PAGES[7]:
        from modules.ui.post_dashboard_page import render as render_dash
        render_dash(result, tpm_thr, cm_thr)

    elif page == POST_PAGES[8]:
        from modules.ui.post_download_page import render as render_dl
        render_dl(
            result,
            st.session_state.get("rates", {}),
            st.session_state.get("click_costs", {}),
            st.session_state.get("prepress", {}),
            float(st.session_state.get("other_pct", 2.0)),
            tpm_thr, cm_thr,
        )

else:
    # ── PreKalkulacja pages ───────────────────────────────────────────────────
    if page == PK_PAGES[0]:
        from modules.ui.prekalk_upload_page import render as render_pk_upload
        render_pk_upload()

    elif page == PK_PAGES[1]:
        from modules.ui.prekalk_tools_page import render as render_pk_tools
        render_pk_tools()

    elif page == PK_PAGES[2]:
        from modules.ui.prekalk_wydajnosc_page import render as render_pk_wy
        render_pk_wy()

    elif page == PK_PAGES[3]:
        from modules.ui.prekalk_preview_page import render as render_pk_pv
        render_pk_pv()

    elif page == PK_PAGES[4]:
        from modules.ui.prekalk_summary_page import render as render_pk_sum
        render_pk_sum()

    elif page == PK_PAGES[5]:
        from modules.ui.prekalk_dashboard_page import render as render_pk_dash
        render_pk_dash()

    elif page == PK_PAGES[6]:
        from modules.ui.prekalk_download_page import render as render_pk_dl
        render_pk_dl()
