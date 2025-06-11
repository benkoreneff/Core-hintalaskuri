# app/main.py
import streamlit as st
import pandas as pd
import io
from parser import load_data, clean_dataframe
from pricing import add_fixed_price_suggestions

# Configure the page
st.set_page_config(
    page_title='Kiinteä hintalaskuri',
    layout='wide'
)

st.title('Kiinteä hintalaskuri')

# --- File Upload ---
uploaded_file = st.file_uploader(
    'Lataa excel tiedosto',
    type=['xlsx', 'xls', 'csv']
)

if uploaded_file:
    try:
        # Load and clean the data
        raw_df = load_data(uploaded_file)
        df = clean_dataframe(raw_df)

        # Compute one‐row‐per‐company summary
        from analytics import compute_company_summary
        stats_df = compute_company_summary(df)

        st.subheader('Yhtiö keskiarvot')
        st.dataframe(stats_df)

        # --- Profit Margin Inputs ---
        st.sidebar.header('Kate asetukset')
        margin_3m = st.sidebar.slider(
            '3-Month Margin (%)', 0, 100, 15
        )
        margin_12m = st.sidebar.slider(
            '12-Month Margin (%)', 0, 100, 10
        )

        # Compute fixed price suggestions
        suggestions_df = add_fixed_price_suggestions(
            stats_df,
            {
                'Avg3Mo': margin_3m,
                'Avg12Mo': margin_12m
            }
        )

        st.subheader('Pricing Suggestions')
        st.dataframe(suggestions_df)

        # --- Export to Excel ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            stats_df.to_excel(writer, sheet_name='Averages', index=False)
            suggestions_df.to_excel(writer, sheet_name='FixedPrices', index=False)
        processed_data = output.getvalue()

        st.download_button(
            label='Download Results as Excel',
            data=processed_data,
            file_name='pricing_results.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        st.error(f'Error processing file: {e}')
else:
    st.info('Please upload an Excel/CSV file to get started.')
