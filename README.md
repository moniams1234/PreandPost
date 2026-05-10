# 📊 Postkalkulacja & PreKalkulacja Profitability App

Production-grade Streamlit financial dashboard for manufacturing profitability analysis.

## 🚀 Uruchomienie lokalne

```bash
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Streamlit Cloud

1. Wgraj repo do GitHub
2. Utwórz aplikację na [share.streamlit.io](https://share.streamlit.io)
3. Ustaw **Main file path** na `app.py`
4. Deploy

## 🗂 Struktura projektu

```
app.py                          # Główny plik wejściowy
modules/
  ui/                           # Strony UI
    post_upload_page.py         # Upload plików PostKalkulacja
    post_rates_page.py          # Stawki rbg
    post_click_costs_page.py    # Koszty klików HP Indigo
    post_prepress_page.py       # Prepress per klient
    post_parameters_page.py     # Parametry globalne
    post_profitability_preview.py # Podgląd z wykresami
    post_summary_page.py        # Podsumowanie miesięczne
    post_dashboard_page.py      # Kokpit trend
    post_download_page.py       # Export Profitability.xlsx
    prekalk_upload_page.py      # Upload PreKalkulacja
    prekalk_tools_page.py       # Edycja Tools / Nesting
    prekalk_wydajnosc_page.py   # Edycja Wydajność
    prekalk_preview_page.py     # Podgląd PreKalkulacja
    prekalk_summary_page.py     # Podsumowanie PreKalkulacja
    prekalk_download_page.py    # Export prekalkulacja.xlsx
    shared.py                   # CSS, stałe, kpi_card()
  calculations/
    profitability_engine.py     # Główny silnik PostKalkulacja
    prekalk_engine.py           # Główny silnik PreKalkulacja
    machine_costs.py            # Arkusz maszyny z PIVOT
    summaries.py                # Podsumowania miesięczne
  exports/
    xlsx_styles.py              # Style openpyxl
    profitability_export.py     # Build Profitability.xlsx
    prekalk_export.py           # Build prekalkulacja.xlsx
  readers/
    generic_reader.py           # Auto-header reader
    baza_reader.py              # Post_list (header=3)
    czasy_reader.py             # Czasy + PIVOT + Stawki
    orders_reader.py            # Orders reader
    tektura_reader.py           # Tektura CSV/XLSX
    material_service_reader.py  # Gilotyna / mindex / cięcia
    tools_reader.py             # Wykrojniki / Nesting
    wydajnosc_reader.py         # Wydajność maszyn
  utils/
    helpers.py                  # sn(), batch_label(), rate_for_machine()
    matching.py                 # fcol() fuzzy column matching
    session.py                  # Persistent uploads
    formatting.py               # is_currency_col()
    validation.py               # check_required_columns()
data/
  default_tools.xlsx            # Domyślna tabela narzędzi (opcjonalnie)
  default_wydajnosc.xlsx        # Domyślna wydajność (opcjonalnie)
.streamlit/
  config.toml                   # maxUploadSize=200, theme
requirements.txt
```

## 📋 Moduły

### PostKalkulacja
Oblicza rentowność na podstawie:
- **Baza (post_list)** — wymagana, nagłówek w wierszu 4
- **Czasy dla aplikacji** — koszty maszyn per zlecenie
- **Zlecenia + faktury** — Sales Value per ZP
- **Faktury linie** — fallback Sales Value
- **Kliki / Inks** — koszt klików HP Indigo
- **Farby Offset** — koszty farb i płyt

Wyniki: TPM, CM, TPM%, CM%, alerty, wykresy, Kokpit, export XLSX.

### PreKalkulacja
Buduje prekalkulację łącząc:
- Dane z PostKalkulacji (Sales Value, ZP, Lewy 10)
- **Orders** — Wykrojnik, Format, Zamawiana ilość
- **Tektura** — cena (m.value/m.qty)
- **Usługa na surowcu** — mindex, liczba cięć
- **Tools** — Nesting per wykrojnik
- **Wydajność** — stawki rbg, wydajności, Miara

Wzory:
- `Liczba arkuszy = Zamawiana ilość / Nesting`
- `Koszt tektury = Liczba arkuszy × cena_tektury`
- `Koszt gilotyny = stawka × (arkusze / cięcia) / wydajność`
- `TPM = Sales Value − Total Materials Cost`
- `CM = TPM − Total DL`

## 🎨 UI

- Sidebar dwumodułowy: PostKalkulacja | PreKalkulacja
- KPI cards, alerty czerwone (TPM% < 60%, CM% < 40%)
- Wykresy Plotly (bar + line trend)
- Edytowalne tabele stawek / wydajności / narzędzi
- Persistentne uploady (nie znikają po zmianie zakładki)

## 📤 Eksporty XLSX

| Plik | Arkusze |
|------|---------|
| `Profitability.xlsx` | Profitability, czasy, Kliki, Farby Offset, Stawki, Koszty klików, Prepress, Parametry, Podsum. YYYY-MM, Batch YYYY-MM, Kokpit |
| `prekalkulacja.xlsx` | prekalkulacja, orders, tektura, usługa na surowcu, tools, wydajność, maszyny, podsumowanie |

## ⚙️ Konfiguracja

`.streamlit/config.toml`:
```toml
[server]
maxUploadSize = 200

[theme]
primaryColor = "#FF5A1F"
backgroundColor = "#F7EFEA"
```
