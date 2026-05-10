"""app6_views.py — reusable app(6)-style summary and dashboard views."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from modules.ui.shared import section_title, kpi_card, BURG, ORG, GRN, RED, LAYOUT


def ensure_month_col(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Miesiąc faktury" not in df.columns:
        if "Data faktury" in df.columns:
            df["Miesiąc faktury"] = pd.to_datetime(df["Data faktury"], errors="coerce").dt.strftime("%Y-%m")
        else:
            df["Miesiąc faktury"] = ""
    df["Miesiąc faktury"] = df["Miesiąc faktury"].astype(str)
    return df


def find_client_col(df: pd.DataFrame, preferred: str | None = None) -> str:
    if preferred and preferred in df.columns:
        return preferred
    for col in ["Klient", "Nazwa klienta", "client_name", "Client", "Klient ID", "Zlecenie produkcyjne"]:
        if col in df.columns:
            return col
    return df.columns[0] if len(df.columns) else "Klient"


def find_do_col(df: pd.DataFrame) -> str | None:
    for col in ["Digital/Offset", "Digital Offset", "Typ druku", "Printing"]:
        if col in df.columns:
            return col
    return None


def find_batch_col(df: pd.DataFrame) -> str | None:
    return "Batch" if "Batch" in df.columns else None


def normalise_financial_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Ensure common financial names exist
    if "Sales Value" not in df.columns:
        for c in ["Sprzedaż", "Suma sprzedaży", "Sales", "sales"]:
            if c in df.columns:
                df["Sales Value"] = df[c]
                break
    if "TPM" not in df.columns and "Suma TPM" in df.columns:
        df["TPM"] = df["Suma TPM"]
    if "CM" not in df.columns and "Suma CM" in df.columns:
        df["CM"] = df["Suma CM"]
    for c in ["Sales Value", "TPM", "CM"]:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def trend_table(df_all: pd.DataFrame, grp_col: str) -> pd.DataFrame:
    df_all = ensure_month_col(normalise_financial_cols(df_all))
    rows = []
    for month in sorted([m for m in df_all["Miesiąc faktury"].dropna().astype(str).unique() if m and m != "NaT"]):
        df_m = df_all[df_all["Miesiąc faktury"].astype(str) == month]
        sv = df_m["Sales Value"].sum()
        tpm = df_m["TPM"].sum()
        cm = df_m["CM"].sum()
        rows.append({
            "Miesiąc": month,
            "Sprzedaż": sv,
            "TPM": tpm,
            "TPM %": tpm / sv if sv else 0,
            "CM": cm,
            "CM %": cm / sv if sv else 0,
            "Klientów": df_m[grp_col].nunique() if grp_col in df_m.columns else 0,
            "Zamówień": len(df_m),
        })
    return pd.DataFrame(rows)


def format_trend(df: pd.DataFrame):
    fmt = {
        "Sprzedaż": "{:,.0f}",
        "TPM": "{:,.0f}",
        "CM": "{:,.0f}",
        "TPM %": "{:.1%}",
        "CM %": "{:.1%}",
    }
    try:
        return df.style.format({k: v for k, v in fmt.items() if k in df.columns})
    except Exception:
        return df


def render_filter_bar(
    df: pd.DataFrame,
    grp_col: str,
    key_prefix: str,
    default_first_month: bool = True,
):
    """App(6)-style filter bar. Returns filtered df, selected months, selected clients."""
    df = ensure_month_col(df)
    months_av = sorted([m for m in df["Miesiąc faktury"].dropna().astype(str).unique() if m and m != "NaT"])

    st.markdown("""
    <div style="background:#FFFFFF;border-radius:14px;padding:16px 22px;
                box-shadow:0 2px 14px rgba(107,0,0,.08);margin-bottom:18px;
                border-left:4px solid #FF5A1F;">
        <div style="font-size:.72rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:.08em;color:#6B0000;margin-bottom:10px;">
            🔍 Filtry kokpitu
        </div>
    </div>
    """, unsafe_allow_html=True)

    frow1, frow2, frow3 = st.columns([1, 1, 2])
    with frow1:
        default_months = months_av[:1] if default_first_month and months_av else months_av
        sel_months = st.multiselect(
            "📅 Miesiące",
            months_av,
            default=default_months,
            key=f"{key_prefix}_months",
        )

    base_months = sel_months if sel_months else months_av
    df_base = df[df["Miesiąc faktury"].isin(base_months)]
    all_clients = sorted(df_base[grp_col].dropna().astype(str).unique()) if grp_col in df_base.columns else []

    with frow2:
        client_mode = st.radio(
            "👤 Widok klientów",
            ["Wszyscy", "Wybrani"],
            horizontal=True,
            key=f"{key_prefix}_client_mode",
        )

    with frow3:
        if client_mode == "Wybrani":
            sel_clients = st.multiselect(
                f"Wybierz klientów ({len(all_clients)} dostępnych)",
                all_clients,
                default=all_clients[:3] if len(all_clients) >= 3 else all_clients,
                key=f"{key_prefix}_clients",
                placeholder="Kliknij i wybierz klientów…",
            )
            if not sel_clients:
                st.caption("⚠️ Nie wybrano klientów — pokazuję wszystkich.")
                sel_clients = all_clients
        else:
            sel_clients = all_clients
            st.markdown(
                f'<div style="padding:8px 0;color:#6B6B6B;font-size:.85rem;">'
                f'✅ Pokazuję wszystkich <b>{len(all_clients)}</b> klientów</div>',
                unsafe_allow_html=True,
            )

    if not sel_months:
        st.info("Wybierz co najmniej jeden miesiąc.")
        st.stop()

    df_all = df[df["Miesiąc faktury"].isin(sel_months)].copy()
    if grp_col in df_all.columns:
        df_all[grp_col] = df_all[grp_col].fillna("(brak)").astype(str)
    if client_mode == "Wybrani" and sel_clients and grp_col in df_all.columns:
        df_all = df_all[df_all[grp_col].isin(sel_clients)]

    return df_all, sel_months, sel_clients


def render_month_kpis(df_all: pd.DataFrame, sel_months: list[str], grp_col: str, tpm_thr: float, cm_thr: float) -> None:
    do_col = find_do_col(df_all)
    for month in sel_months:
        df_m = df_all[df_all["Miesiąc faktury"].astype(str) == str(month)].copy()
        if df_m.empty:
            continue
        st.markdown("<hr style='margin:28px 0 20px;border-color:rgba(107,0,0,.18);'>", unsafe_allow_html=True)
        st.markdown(f'<div class="stitle">🗓️ {month}</div>', unsafe_allow_html=True)

        sv_tot = df_m["Sales Value"].sum()
        tpm_tot = df_m["TPM"].sum()
        cm_tot = df_m["CM"].sum()
        tpm_pct = tpm_tot / sv_tot * 100 if sv_tot else 0
        cm_pct = cm_tot / sv_tot * 100 if sv_tot else 0
        n_kl = df_m[grp_col].nunique() if grp_col in df_m.columns else 0
        n_ord = len(df_m)
        n_dig = int((df_m[do_col] == "Digital").sum()) if do_col else 0
        n_off = int((df_m[do_col] == "Offset").sum()) if do_col else 0
        n_nop = int((df_m[do_col] == "no printing").sum()) if do_col else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.markdown(kpi_card(f"{sv_tot:,.0f} PLN", "Sprzedaż", ""), unsafe_allow_html=True)
        k2.markdown(kpi_card(f"{tpm_tot:,.0f} PLN", "TPM", ""), unsafe_allow_html=True)
        k3.markdown(kpi_card(f"{tpm_pct:.1f}%", "TPM %", "g" if tpm_pct >= tpm_thr else "r"), unsafe_allow_html=True)
        k4.markdown(kpi_card(f"{cm_tot:,.0f} PLN", "CM", ""), unsafe_allow_html=True)
        k5.markdown(kpi_card(f"{cm_pct:.1f}%", "CM %", "g" if cm_pct >= cm_thr else "r"), unsafe_allow_html=True)

        b1, b2, b3, b4, b5 = st.columns(5)
        b1.markdown(kpi_card(str(n_kl), "Klientów", "o"), unsafe_allow_html=True)
        b2.markdown(kpi_card(str(n_ord), "Zamówień", ""), unsafe_allow_html=True)
        b3.markdown(kpi_card(str(n_dig), "Digital", ""), unsafe_allow_html=True)
        b4.markdown(kpi_card(str(n_off), "Offset", ""), unsafe_allow_html=True)
        b5.markdown(kpi_card(str(n_nop), "No printing", ""), unsafe_allow_html=True)


def render_main_trend_charts(df_all: pd.DataFrame, grp_col: str, tpm_thr: float, cm_thr: float) -> None:
    section_title("🗓️ Trend miesięczny")
    df_kok = trend_table(df_all, grp_col)
    st.dataframe(format_trend(df_kok), use_container_width=True)

    if not df_kok.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(
                df_kok, x="Miesiąc", y="Sprzedaż",
                title="Sprzedaż miesięczna",
                color_discrete_sequence=[BURG],
                markers=True,
            )
            fig.update_layout(**LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.line(
                df_kok, x="Miesiąc", y=["TPM %", "CM %"],
                title="TPM% i CM% miesięcznie",
                markers=True,
                color_discrete_sequence=[GRN, ORG],
            )
            fig.add_hline(y=tpm_thr / 100, line_dash="dash", line_color=RED,
                          annotation_text=f"TPM próg {tpm_thr:.0f}%")
            fig.add_hline(y=cm_thr / 100, line_dash="dash", line_color="gray",
                          annotation_text=f"CM próg {cm_thr:.0f}%")
            fig.update_layout(**LAYOUT, yaxis_tickformat=".1%")
            st.plotly_chart(fig, use_container_width=True)


def render_detail_charts(df_m: pd.DataFrame, grp_col: str, tpm_thr: float, cm_thr: float) -> None:
    if df_m.empty or grp_col not in df_m.columns:
        return

    grp = df_m.groupby(grp_col).agg(
        sv=("Sales Value", "sum"),
        tpm=("TPM", "sum"),
        cm=("CM", "sum"),
        n=("Sales Value", "count"),
    ).reset_index()
    grp["tpm_pct"] = grp["tpm"] / grp["sv"].replace(0, np.nan) * 100
    grp["cm_pct"] = grp["cm"] / grp["sv"].replace(0, np.nan) * 100
    grp = grp.fillna(0)

    app6_layout = dict(
        plot_bgcolor="white",
        paper_bgcolor="white",
        title_font_color=BURG,
        title_font_size=16,
        height=310,
        margin=dict(t=48, b=38, l=36, r=14),
        font=dict(color="#4b5563"),
    )

    st.markdown('<div class="stitle">📊 Wykresy szczegółowe</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        fig = px.bar(grp.nlargest(5, "tpm"), x=grp_col, y="tpm",
                     title="🏆 Top 5 wg TPM", color_discrete_sequence=[BURG])
        fig.update_layout(**app6_layout)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(grp.nlargest(5, "cm"), x=grp_col, y="cm",
                     title="🏆 Top 5 wg CM", color_discrete_sequence=[ORG])
        fig.update_layout(**app6_layout)
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        fig = px.bar(grp.nlargest(5, "sv"), x=grp_col, y="sv",
                     title="🏆 Top 5 wg sprzedaży", color_discrete_sequence=[GRN])
        fig.update_layout(**app6_layout)
        st.plotly_chart(fig, use_container_width=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        do_col = find_do_col(df_m)
        if do_col:
            do_counts = df_m[do_col].fillna("(brak)").value_counts().reset_index()
            do_counts.columns = ["Typ", "Liczba"]
            fig = px.pie(do_counts, names="Typ", values="Liczba",
                         title="🖨 Digital / Offset / No printing",
                         color_discrete_sequence=[BURG, ORG, RED, GRN])
            fig.update_layout(paper_bgcolor="white", title_font_color=BURG,
                              title_font_size=16, height=310,
                              margin=dict(t=48, b=38, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
    with c5:
        fig = px.bar(grp.sort_values("tpm_pct", ascending=False),
                     x=grp_col, y="tpm_pct",
                     title="TPM % wg klientów", color_discrete_sequence=[BURG])
        fig.add_hline(y=tpm_thr, line_dash="dash", line_color=ORG,
                      annotation_text=f"Próg {tpm_thr:.0f}%",
                      annotation_font_color=ORG)
        fig.update_layout(**app6_layout, yaxis_ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)
    with c6:
        fig = px.bar(grp.sort_values("cm_pct", ascending=False),
                     x=grp_col, y="cm_pct",
                     title="CM % wg klientów", color_discrete_sequence=[GRN])
        fig.add_hline(y=cm_thr, line_dash="dash", line_color=RED,
                      annotation_text=f"Próg {cm_thr:.0f}%",
                      annotation_font_color=RED)
        fig.update_layout(**app6_layout, yaxis_ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)

    c7, c8 = st.columns(2)
    with c7:
        fig = px.bar(grp.sort_values("n", ascending=False),
                     x=grp_col, y="n",
                     title="Liczba zamówień wg klientów",
                     color_discrete_sequence=[ORG])
        fig.update_layout(**app6_layout)
        st.plotly_chart(fig, use_container_width=True)
    with c8:
        batch_col = find_batch_col(df_m)
        if batch_col:
            df_bat = df_m.groupby([grp_col, batch_col]).size().reset_index(name="n")
            pivot = df_bat.pivot(index=grp_col, columns=batch_col, values="n").fillna(0)
            fig = px.imshow(pivot, title="Zamówienia: Klient × Batch",
                            color_continuous_scale=["white", BURG], aspect="auto")
            fig.update_layout(paper_bgcolor="white", title_font_color=BURG,
                              title_font_size=16, height=310,
                              margin=dict(t=48, b=38, l=36, r=14))
            st.plotly_chart(fig, use_container_width=True)


def render_alerts(df_m: pd.DataFrame, grp_col: str, tpm_thr: float, cm_thr: float) -> None:
    if df_m.empty or grp_col not in df_m.columns:
        return
    grp = df_m.groupby(grp_col).agg(
        sv=("Sales Value", "sum"),
        tpm=("TPM", "sum"),
        cm=("CM", "sum"),
    ).reset_index()
    grp["TPM %"] = grp["tpm"] / grp["sv"].replace(0, np.nan) * 100
    grp["CM %"] = grp["cm"] / grp["sv"].replace(0, np.nan) * 100
    grp = grp.fillna(0)

    section_title("⚠️ Alerty")
    a1, a2 = st.columns(2)
    with a1:
        st.markdown(f"**TPM % poniżej {tpm_thr:.0f}%**")
        out = grp[grp["TPM %"] < tpm_thr][[grp_col, "sv", "tpm", "TPM %"]].rename(
            columns={grp_col: "Klient", "sv": "Sprzedaż", "tpm": "TPM"})
        if out.empty:
            st.success("Brak alertów TPM ✓")
        else:
            st.dataframe(out.style.format({"Sprzedaż": "{:,.0f}", "TPM": "{:,.0f}", "TPM %": "{:.1f}%"}),
                         use_container_width=True)
    with a2:
        st.markdown(f"**CM % poniżej {cm_thr:.0f}%**")
        out = grp[grp["CM %"] < cm_thr][[grp_col, "sv", "cm", "CM %"]].rename(
            columns={grp_col: "Klient", "sv": "Sprzedaż", "cm": "CM"})
        if out.empty:
            st.success("Brak alertów CM ✓")
        else:
            st.dataframe(out.style.format({"Sprzedaż": "{:,.0f}", "CM": "{:,.0f}", "CM %": "{:.1f}%"}),
                         use_container_width=True)


def render_app6_dashboard(df: pd.DataFrame, grp_col: str, tpm_thr: float, cm_thr: float, key_prefix: str) -> None:
    df = ensure_month_col(normalise_financial_cols(df))
    df_all, sel_months, _ = render_filter_bar(df, grp_col, key_prefix=key_prefix, default_first_month=True)

    if df_all.empty:
        st.info("Brak danych dla wybranych filtrów.")
        return

    render_month_kpis(df_all, sel_months, grp_col, tpm_thr, cm_thr)
    render_main_trend_charts(df_all, grp_col, tpm_thr, cm_thr)
    render_detail_charts(df_all, grp_col, tpm_thr, cm_thr)
    render_alerts(df_all, grp_col, tpm_thr, cm_thr)


def render_app6_summary(df: pd.DataFrame, grp_col: str, tpm_thr: float, cm_thr: float, key_prefix: str) -> None:
    df = ensure_month_col(normalise_financial_cols(df))
    months_av = sorted([m for m in df["Miesiąc faktury"].dropna().astype(str).unique() if m and m != "NaT"])

    sel_months = st.multiselect(
        "Wybierz miesiące do podsumowania",
        months_av,
        default=months_av[:3] if len(months_av) >= 3 else months_av,
        key=f"{key_prefix}_summary_months",
    )
    if not sel_months:
        st.info("Wybierz co najmniej jeden miesiąc.")
        st.stop()

    do_col = find_do_col(df)
    batch_col = find_batch_col(df)

    for month in sel_months:
        st.markdown(f'<div class="stitle">📅 {month}</div>', unsafe_allow_html=True)
        df_m = df[df["Miesiąc faktury"].astype(str) == str(month)].copy()
        if df_m.empty:
            st.info(f"Brak danych dla {month}")
            continue
        if grp_col not in df_m.columns:
            st.warning(f"Brak kolumny klienta '{grp_col}'")
            continue

        df_m[grp_col] = df_m[grp_col].fillna("(brak)").astype(str)
        rows_s = []
        for kl, grp in df_m.groupby(grp_col):
            sv = grp["Sales Value"].sum()
            tpm = grp["TPM"].sum()
            cm = grp["CM"].sum()
            rows_s.append({
                "Klient": kl,
                "Sprzedaż": round(sv, 2),
                "TPM": round(tpm, 2),
                "TPM %": f"{tpm/sv*100:.1f}%" if sv else "—",
                "CM": round(cm, 2),
                "CM %": f"{cm/sv*100:.1f}%" if sv else "—",
                "Zamówień": len(grp),
                "Digital": int((grp[do_col] == "Digital").sum()) if do_col else 0,
                "Offset": int((grp[do_col] == "Offset").sum()) if do_col else 0,
                "No printing": int((grp[do_col] == "no printing").sum()) if do_col else 0,
            })
        df_s = pd.DataFrame(rows_s)

        sv_t = df_s["Sprzedaż"].sum() if not df_s.empty else 0
        tpm_t = df_s["TPM"].sum() if not df_s.empty else 0
        cm_t = df_s["CM"].sum() if not df_s.empty else 0
        df_s.loc[len(df_s)] = {
            "Klient": "━━ SUMA",
            "Sprzedaż": round(sv_t, 2),
            "TPM": round(tpm_t, 2),
            "TPM %": f"{tpm_t/sv_t*100:.1f}%" if sv_t else "—",
            "CM": round(cm_t, 2),
            "CM %": f"{cm_t/sv_t*100:.1f}%" if sv_t else "—",
            "Zamówień": int(df_s["Zamówień"].sum()) if "Zamówień" in df_s.columns else 0,
            "Digital": int(df_s["Digital"].sum()) if "Digital" in df_s.columns else 0,
            "Offset": int(df_s["Offset"].sum()) if "Offset" in df_s.columns else 0,
            "No printing": int(df_s["No printing"].sum()) if "No printing" in df_s.columns else 0,
        }

        sc1, sc2 = st.columns([3, 1])
        with sc1:
            st.dataframe(
                df_s.style.format({"Sprzedaż": "{:,.2f}", "TPM": "{:,.2f}", "CM": "{:,.2f}"}),
                use_container_width=True,
            )
        with sc2:
            st.markdown("**Zamówienia · Batch × Klient**")
            if batch_col:
                df_bat = df_m.groupby([grp_col, batch_col]).size().reset_index(name="n")
                st.dataframe(df_bat, use_container_width=True, height=340)
            else:
                st.caption("Brak kolumny Batch.")
