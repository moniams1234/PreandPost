"""prekalk_download_page.py — PreKalkulacja Pobierz XLSX page."""
from __future__ import annotations

import streamlit as st
from modules.exports.prekalk_export import export_prekalkulacja_xlsx


def render() -> None:
    st.markdown("# 💾 PreKalkulacja — Pobierz XLSX")

    pk_res = st.session_state.get("pk_result")
    if pk_res is None:
        st.warning("⚠️ Brak danych. Przejdź do **PreKalkulacja – Upload** i przelicz.")
        st.stop()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        "Kliknij **Generuj**, aby zbudować plik **prekalkulacja.xlsx** "
        "ze wszystkimi arkuszami i formatowaniem."
    )

    if st.button("🔄 Generuj prekalkulacja.xlsx", key="_pk_gen_xlsx_dl"):
        with st.spinner("Budowanie pliku…"):
            buf = export_prekalkulacja_xlsx(
                pk_res["df_pk"],
                pk_res.get("df_orders"),
                pk_res.get("df_tektura"),
                pk_res.get("df_material"),
                pk_res.get("df_tools"),
                pk_res.get("df_wydajnosc"),
                pk_res.get("df_maszyny"),
                tpm_thr=st.session_state.get("tpm_thr", 60.0),
                cm_thr=st.session_state.get("cm_thr",  40.0),
            )
        st.success("✅ Plik gotowy!")
        st.download_button(
            label="⬇️ Pobierz prekalkulacja.xlsx",
            data=buf,
            file_name="prekalkulacja.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="_pk_dl_btn",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### 📋 Zawartość pliku")
    st.markdown("""
<div class="card">
<table style="width:100%;font-size:.87rem;border-collapse:collapse;">
<tr style="background:#3A0000;color:#fff;">
  <th style="padding:8px;text-align:left">Arkusz</th>
  <th style="padding:8px;text-align:left">Opis</th>
</tr>
<tr style="background:#F7EFEA"><td style="padding:7px"><b>prekalkulacja</b></td>
  <td>Główna tabela · Liczba arkuszy · Koszty · TPM · CM · filtry · nagłówki</td></tr>
<tr><td style="padding:7px"><b>orders</b></td>
  <td>Surowe dane Orders (Wykrojnik, Format, Klient…)</td></tr>
<tr style="background:#F7EFEA"><td style="padding:7px"><b>tektura</b></td>
  <td>Dane tektury z ceną (m.value/m.qty)</td></tr>
<tr><td style="padding:7px"><b>usługa na surowcu</b></td>
  <td>Dane gilotyny z mindex i liczbą cięć</td></tr>
<tr style="background:#F7EFEA"><td style="padding:7px"><b>tools</b></td>
  <td>Tabela narzędzi z Nestingiem</td></tr>
<tr><td style="padding:7px"><b>wydajność</b></td>
  <td>Stawki rbg i wydajności maszyn</td></tr>
<tr style="background:#F7EFEA"><td style="padding:7px"><b>maszyny</b></td>
  <td>Pivot z czasy + Wydajność i Miara</td></tr>
<tr><td style="padding:7px"><b>podsumowanie</b></td>
  <td>KPI miesięczne per klient · TPM% · CM% · formatowanie warunkowe</td></tr>
</table>
</div>
""", unsafe_allow_html=True)

    df_pk = pk_res["df_pk"]
    sv  = df_pk["Sales Value"].sum()
    tpm = df_pk["TPM"].sum()
    cm  = df_pk["CM"].sum()
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Rekordów",    f"{len(df_pk):,}")
    s2.metric("Miesięcy",    df_pk["Miesiąc faktury"].nunique()
              if "Miesiąc faktury" in df_pk.columns else 0)
    s3.metric("Sales Value", f"{sv:,.0f}")
    s4.metric("TPM",         f"{tpm:,.0f}")
    s5.metric("CM",          f"{cm:,.0f}")
