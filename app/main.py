# app/main.py

import streamlit as st
import pandas as pd
import io
from io import BytesIO
from parser import load_data, clean_dataframe
from analytics import compute_company_summary
from analytics import monthly_totals
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from pricing import add_fixed_price_suggestions
from PIL import Image
import hashlib

logo = Image.open('app/Taopa logo.png')

# --- Read + clean + summarise only once per file ----------------------------
@st.cache_data(show_spinner="📂 Luetaan Excel-tiedostoa …")
def prep_everything(file_bytes: bytes, use_vat: bool):
    """
    Returns: df_clean, summary_df, monthly_tbl
    """
    df_np = load_data(BytesIO(file_bytes),
                      sheet_name="Netvisor + Procountor 2024-2025")
    df_fn = load_data(BytesIO(file_bytes),
                      sheet_name="Fennoa 2024-2025")
    df_raw   = pd.concat([df_np, df_fn], ignore_index=True)
    df_clean = clean_dataframe(df_raw)

    # ----- DROP rows where company name starts with ":" ---------------
    df_clean = df_clean[
        ~df_clean["Yrityksen nimi"].str.startswith(":", na=False)
    ]

    if not use_vat:
        df_clean["Summa"] = df_clean["Ilman ALV"]

    summary_df  = compute_company_summary(df_clean)
    monthly_tbl = monthly_totals(df_clean)
    return df_clean, summary_df, monthly_tbl

# Sivun asetukset
st.set_page_config(
    page_title='Ohjelmistokustannukset',
    layout='wide'
)



# Make two columns, narrow one for logo, wide one for title
col1, col2 = st.columns([1, 6])
with col1:
    st.image(logo, width=200)        # adjust width to taste
with col2:
    st.title("Asiakkaiden ohjelmistokustannukset")

    st.markdown(
        """
        Tällä työkalulla voit laskea yrityskohtaiset kuukausittaiset ohjelmistokustannukset historiatietojen perusteella sekä tarkastella niiden keskiarvoja. 
        Yrityslistauksesta klikkaamalla näet lisätietoja valitusta yrityksestä, mukaan lukien kustannusten kehityksen ja yksityiskohtaisen erittelyn.

        Sivuvalikosta löydät kiinteähintaisen laskurin, joka ehdottaa tarjouksia valitsemillasi voittomarginaaleilla. 
        Voit ladata Netvisor-, Procountor- tai Fennoa-tiedot Excel-muodossa, valita haluamasi tilastot ja suodatusasetukset sivupaneelista, 
        ja sovellus laskee hinnat sekä nostaa esiin mahdolliset muutokset ohjelmistokustannuksissa.
        """
    )

# --- Tiedoston lataus ---
uploaded_file = st.file_uploader(
    'Lataa Excel-tiedosto',
    type=['xlsx', 'xls', 'csv']
)

if uploaded_file:
    try:
        # Lue tiedoston bitit
        data_bytes = uploaded_file.read()

        st.sidebar.header("Asetukset")

        show_ended = st.sidebar.checkbox(
            "Näytä päättyneet asiakkuudet",
            value=False,
            help=(
                "Jos valitsematta, taulukko ja hinnoittelulaskuri "
                "näyttävät vain aktiiviset asiakkuudet."
            ),
        )

        # — ALV-hinta – switch: kun ei valittuna, käytetään 'Ilman ALV' * 'Määrä' summaan —
        use_vat = st.sidebar.checkbox(
        'ALV-hinta',
        value = False,
        help = (
        'Jos ei valittuna, lasketaan hinnat Excelin '
        '"Ilman ALV"–sarakkeesta (kertomalla määrällä). '
        'Jos valittuna, käytetään alkuperäistä Summa-saraketta (sis. ALV).'
        )
        )


        df_clean, summary_df, monthly_tbl = prep_everything(data_bytes, use_vat)

        # --- Suodata pois päättyneet asiakkuudet, jos valinta EI ole päällä ----------
        if not show_ended:
            # Viimeisin kuukausi koko aineistossa, esim. 2025-05-01
            last_period = df_clean["Kuukausi"].max()

            # Yritykset, joilla on rivejä tuolle kuulle
            active_ids = (
                df_clean.loc[df_clean["Kuukausi"] == last_period, "Y-tunnus"]
                .unique()
            )

            # Pidä ainoastaan aktiivisten yritysten rivit
            df_clean = df_clean[df_clean["Y-tunnus"].isin(active_ids)].copy()

            # Laske summary- ja monthly-taulut uudelleen rajatusta datasta
            summary_df = compute_company_summary(df_clean)
            monthly_tbl = monthly_totals(df_clean)

        # -----------------------------------------------------------
        # Poista hyvityslaskujen "asiakkaat" (negatiivinen keskiarvo)
        # -----------------------------------------------------------
        neg_ids = summary_df.loc[summary_df["AvgAll"] < 0, "Y-tunnus"].unique()

        summary_df = summary_df[summary_df["AvgAll"] >= 0].copy()
        monthly_tbl = monthly_tbl[~monthly_tbl["Y-tunnus"].isin(neg_ids)].copy()
        df_clean = df_clean[~df_clean["Y-tunnus"].isin(neg_ids)].copy()
        # -----------------------------------------------------------

        # Lokalisoidaan sarakenimet suomeksi
        summary_localized = summary_df.rename(columns={
            'Program': 'Ohjelmisto',
            'DateRange': 'Ajanjakso',
            'AvgAll': 'Keskiarvo kaikilta kuukausilta',
            'Avg3Mo': '3 kk keskiarvo',
            'Std3Mo': '3 kk keskihajonta',
            'CV3Mo': '3 kk vaihteluaste',
            'Avg12Mo': '12 kk keskiarvo',
            'Std12Mo': '12 kk keskihajonta',
            'CV12Mo': '12 kk vaihteluaste',
            'GrowthRatio': 'Kasvusuhde',
            'Seasonality': 'Kausivaihtelusuhde'
        })


        # 1) määritellään mitkä sarakkeet ovat rahaa ja mitkä tilastoja
        currency_cols = [
            'Keskiarvo kaikilta kuukausilta',
            '3 kk keskiarvo',
            '12 kk keskiarvo'
        ]
        stat_cols = [
            '3 kk keskihajonta',
            '12 kk keskihajonta',
            '3 kk vaihteluaste',
            '12 kk vaihteluaste',
            'Kasvusuhde',
            'Kausivaihtelusuhde'
        ]

        st.subheader('Yritysten ohjelmistokustannusten kuukausittaiset keskiarvot')

        # --- Pikahaku koko tauluun ---
        search_query = st.text_input(
            "🔍 Haku (yhtiön nimi, tunnus …)",
            placeholder="Kirjoita hakusana"
        )

        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

        # ── 1)  Build grid options ──────────────────────────────────────────────
        gb = GridOptionsBuilder.from_dataframe(summary_localized)

        # allow row click-selection
        gb.configure_selection(selection_mode="single", use_checkbox=False)

        # default column behaviour: resizable & header can wrap
        gb.configure_default_column(
            resizable=True,
            wrapHeaderText=True,
            autoHeaderHeight=True
        )

        # euro / stats formatting (your existing loops stay untouched here)
        for c in currency_cols:
            gb.configure_column(
                c,
                type=["numericColumn"],
                valueFormatter="x.toLocaleString('fi-FI',{style:'currency',currency:'EUR',minimumFractionDigits:2})"
            )
        for c in stat_cols:
            gb.configure_column(
                c,
                type=["numericColumn"],
                valueFormatter="x.toFixed(2)"
            )

        # JS hook: auto-size every column once data is rendered
        auto_size_js = JsCode("""
        function(params) {
            const all = [];
            params.columnApi.getAllColumns().forEach(col => all.push(col.colId));
            params.columnApi.autoSizeColumns(all, false);   // 'false' keeps scroll
        }
        """)
        gb.configure_grid_options(onFirstDataRendered=auto_size_js)

        grid_opts = gb.build()

        # Välitetään hakusana AG Gridille
        grid_opts["quickFilterText"] = search_query

        # ── 2)  Display the grid ────────────────────────────────────────────────
        grid_resp = AgGrid(
            summary_localized,
            gridOptions=grid_opts,
            update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.SELECTION_CHANGED,
            height=400,
            fit_columns_on_grid_load=False,  # keep columns wider than viewport
            allow_unsafe_jscode=True  # 💡 let JsCode through
        )

        # guard against None / DataFrame return types
        sel = grid_resp.get("selected_rows", [])
        if isinstance(sel, pd.DataFrame):
            selected = sel.to_dict("records")
        else:
            selected = sel or []

        # — DETALJINÄKYMÄ VALITULLE YRITYKSELLE —
        if selected:
            row = selected[0]
            comp_id = row["Y-tunnus"]
            comp_name = row["Yrityksen nimi"]

            st.markdown("---")
            st.subheader(f"📊 Lisätiedot: {comp_name}")

            # 1) Kulujen kehitys kuukausittain
            series = (
                monthly_tbl.query("`Y-tunnus` == @comp_id")
                .set_index("Kuukausi")["MonthlySum"]
            )
            st.subheader("Ohjelmistokustannukset kuukausittain")
            st.line_chart(series, height=250)

            # ─────────────────────────────────────────────────────────────
            # 3) Tuotekohtainen erittely yhdelle kuukaudelle
            # ─────────────────────────────────────────────────────────────
            comp_df = df_clean[df_clean["Y-tunnus"] == comp_id].copy()

            # ➊ period-helper only once
            comp_df["Kuukausi_Period"] = comp_df["Kuukausi"].dt.to_period("M")

            # ➋ month selector
            months_periods = comp_df["Kuukausi_Period"].sort_values().unique()
            month_names = [p.strftime("%b-%Y") for p in months_periods]

            selected_name = st.selectbox(
                "Valitse kuukausi erittelyyn",
                options=month_names,
                index=len(month_names) - 1
            )
            selected_period = months_periods[month_names.index(selected_name)]

            # ➌ breakdown with total €
            breakdown = (
                comp_df[comp_df["Kuukausi_Period"] == selected_period]
                .groupby("Tuote", as_index=False)
                .agg(
                    Määrä=("Määrä", "sum"),
                    Hinta=("Hinta", "first")  # €/kpl (within a product it's constant)
                )
            )
            breakdown["Yhteensä"] = breakdown["Määrä"] * breakdown["Hinta"]
            breakdown = breakdown.sort_values("Yhteensä", ascending=False)

            # ➍ display
            st.subheader(f"Tuotekohtainen erittely – {selected_name}")
            st.dataframe(
                breakdown.reset_index(drop=True).style.format({
                    "Määrä": "{:.0f}",
                    "Hinta": "€{:.2f}",
                    "Yhteensä": "€{:.2f}"
                }),
                hide_index=True
            )

            # --- RE-DISPLAY LAST PRICING RESULTS (if any) ---

            if "pricing_df" in st.session_state:
                st.subheader("Hinnoitteluehdotukset")
                st.dataframe(st.session_state["pricing_df"])




        # --- Hinnoitteluasetukset ---
        with st.sidebar.form('pricing_form'):
            st.header('Kiinteähinta- laskuri')

            # — always visible —
            margin_pct = st.slider('Voittomarginaali (%)', 0, 100, 15)

            programs = ['Kaikki'] + sorted(summary_df['Program'].unique().tolist())
            program_choice = st.selectbox('Valitse ohjelmisto', programs)

            base_df = (
                summary_df
                if program_choice == 'Kaikki'
                else summary_df[summary_df['Program'] == program_choice]
            )
            companies = base_df['Yrityksen nimi'].unique().tolist()
            selected_companies = st.multiselect(
                'Valitse yritykset (valinnainen)',
                options=companies,
                default=[]
            )

            # — NEW: choose which flags to **display** —
            st.markdown("**Näytä indikaattorit**")
            show_volatility = st.checkbox('Korkea volatiliteetti', value=True)
            show_growth = st.checkbox('Voimakas kasvu', value=True)
            show_decline = st.checkbox('Voimakas lasku', value=True)
            show_seasonality = st.checkbox('Korkea kausivaihtelu', value=True)

            # — old filtering options tucked in Lisäasetukset —
            with st.expander('Lisäasetukset'):
                avg_options = [
                    'AvgAll',
                    'Avg3Mo', 'Std3Mo', 'CV3Mo',
                    'Avg12Mo', 'Std12Mo', 'CV12Mo',
                ]
                selected_avgs = st.multiselect(
                    'Valitse tilastot hinnoitteluun',
                    options=avg_options,
                    default=['Avg3Mo', 'Avg12Mo'],
                    help='Valitse yksi tai useampi keskiarvo, joihin marginaali kohdistetaan'
                )
                growth_thresh = st.slider('Korkean kasvusuhteen kynnys', 1.0, 2.0, 1.20, 0.01)
                decline_thresh = st.slider('Voimakkaan laskusuhteen kynnys', 0.0, 1.0, 0.80, 0.01)
                vol_thresh = st.slider('Korkean volatiliteetin CV-kynnys', 0.0, 1.0, 0.25, 0.01)
                season_thresh = st.slider('Korkean kausivaihtelun amplitudikynnys', 0.0, 5.0, 2.0, 0.01)


                filter_low_vol = st.checkbox('Poista korkean volatiliteetin yritykset', value=False)
                filter_strong_growth = st.checkbox('Vain voimakkaasti kasvaneet yritykset', value=False)
                filter_high_season = st.checkbox('Poista korkean kausivaihtelun yritykset', value=False)

            calculate = st.form_submit_button('Laske hinnoittelu')

        if calculate:
            if not selected_avgs:
                st.warning('Valitse vähintään yksi keskiarvotyyppi hinnoittelua varten.')
            else:
                # 1) perus-suodatus ohjelmiston ja yritysten mukaan
                base = (
                    summary_df
                    if program_choice == 'Kaikki'
                    else summary_df[summary_df['Program'] == program_choice]
                )
                filtered = (
                    base.copy()
                    if not selected_companies
                    else base[base['Yrityksen nimi'].isin(selected_companies)].copy()
                )

                # 2) laske **kaikki** liput
                filtered['High Volatility'] = filtered['CV3Mo'] > vol_thresh
                filtered['Strong Growth'] = filtered['GrowthRatio'] > growth_thresh
                filtered['High Seasonality'] = filtered['Seasonality'] > season_thresh
                # “Voimakas lasku” käänteinen kasvu:
                filtered['StrongDecline'] = filtered['GrowthRatio'] < decline_thresh

                # 3) sovella vain LISÄASETUKSET‐suodattimet
                if filter_low_vol:
                    filtered = filtered[~filtered['High Volatility']]
                if filter_strong_growth:
                    filtered = filtered[filtered['Strong Growth']]
                if filter_high_season:
                    filtered = filtered[~filtered['High Seasonality']]

                # 4) kopioi ja laske marginaalisarakkeet
                suggestions_df = filtered.copy()
                original_margin_cols = []
                for avg in selected_avgs:
                    dst = f"{avg}_With{margin_pct:.0f}Pct"
                    suggestions_df[dst] = suggestions_df[avg] * (1 + margin_pct / 100.0)
                    original_margin_cols.append(dst)

                # 5) valitse näyttö-sarakkeet:
                id_cols = ['Y-tunnus', 'Yrityksen nimi', 'Program', 'DateRange']
                avg_cols = selected_avgs
                margin_cols = original_margin_cols

                # figure out which flags to **include** in the output:
                flag_cols = []
                if show_volatility:  flag_cols.append('High Volatility')
                if show_growth:      flag_cols.append('Strong Growth')
                if show_decline:     flag_cols.append('StrongDecline')
                if show_seasonality: flag_cols.append('High Seasonality')

                # map originals → Finnish names, including new “Strong Decline”
                rename_map = {
                    'Program': 'Ohjelmisto',
                    'DateRange': 'Ajanjakso',
                    'High Volatility': 'Korkea volatiliteetti',
                    'Strong Growth': 'Voimakas kasvu',
                    'StrongDecline': 'Voimakas lasku',
                    'High Seasonality': 'Korkea kausivaihtelu',
                    **{dst: f"{avg}_marginaali (%)" for avg, dst in zip(selected_avgs, margin_cols)}
                }

                display_df = suggestions_df[id_cols + avg_cols + margin_cols + flag_cols] \
                    .rename(columns=rename_map)

                # 6) styling & formatting
                st.subheader('Hinnoitteluehdotukset')

                # 6) highlight logic for margin columns (already renamed)
                display_margin_cols = [rename_map[dst] for dst in margin_cols]


                def highlight_max_min(row):
                    vals = [row[c] for c in display_margin_cols]
                    mx, mn = max(vals), min(vals)
                    return [
                        'background-color: #d7f1e5' if v == mx
                        else 'background-color: #ffd6cb' if v == mn
                        else ''
                        for v in vals
                    ]


                # start styling with margin highlights + currency formatting
                styled = display_df.style.apply(
                    highlight_max_min,
                    axis=1,
                    subset=display_margin_cols
                ).format(
                    {c: "€{:.2f}" for c in avg_cols + display_margin_cols}
                )


                # --- Define style_flag here so it's in scope ---
                def style_flag(val):
                    return 'background-color: #d9d9d9; color: #ffb4a0;' if val else ''


                # Build a list of your Finnish‐named flag columns
                display_flag_cols = []
                if show_volatility:  display_flag_cols.append('Korkea volatiliteetti')
                if show_growth:      display_flag_cols.append('Voimakas kasvu')
                if show_decline:     display_flag_cols.append('Voimakas lasku')
                if show_seasonality: display_flag_cols.append('Korkea kausivaihtelu')

                # 7) darken the checked‐box cells in those flag columns
                styled = styled.applymap(
                    style_flag,
                    subset=display_flag_cols
                )

                st.session_state["pricing_df"] = styled  # <-- persist

                # 8) render the styled table
                st.dataframe(styled)

                # 7) Excel‐export unchanged…
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    filtered.to_excel(writer, sheet_name='Keskiarvot', index=False)
                    display_df.to_excel(writer, sheet_name='Kiinteät hinnat', index=False)
                processed_data = output.getvalue()

                st.download_button(
                    'Lataa tulokset Excelinä',
                    data=processed_data,
                    file_name='pricing_results.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

        else:
            st.sidebar.info('Säädä asetukset lomakkeessa ja klikkaa "Laske hinnoittelu"')


    except Exception as e:
        st.error(f'Tiedoston käsittelyssä tapahtui virhe: {e}')
else:
    st.info('Lataa Excel- tai CSV-tiedosto aloittaaksesi.')
