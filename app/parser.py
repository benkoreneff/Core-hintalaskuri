
import pandas as pd
import re

def load_data(path: str, sheet_name: str = 0) -> pd.DataFrame:
    """
    Load the raw Excel data.
    """
    # engine openpyxl handles xlsx
    df = pd.read_excel(path, sheet_name=sheet_name, engine='openpyxl')
    return df

def _clean_money_column(series: pd.Series) -> pd.Series:
    """
    Remove currency symbols and thousand separators, convert comma-decimal to float.
    E.g. '1 234,56 €' → 1234.56
    """
    # Remove everything except digits, comma, dot, minus
    cleaned = (
        series
        .astype(str)
        .str.replace(r'[^0-9\-,\.]', '', regex=True)
        # if comma used as decimal separator, swap to dot
        .str.replace(r'(\d+),(\d{1,2})$', r'\1.\2', regex=True)
    )
    return pd.to_numeric(cleaned, errors='coerce')

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Take the raw df, clean columns, parse dates and numbers.
    """
    df = df.copy()
    # Standardize column names
    df.columns = [col.strip() for col in df.columns]

    # Parse month: 'Jan-24' → datetime(2024-01-01)
    df['Kuukausi'] = pd.to_datetime(
        df['Kuukausi'], format='%b-%y', errors='coerce'
    ) + pd.offsets.MonthBegin(0)

    # Clean numeric columns
    money_cols = ['Hinta', 'Ilman ALV', 'ALV', 'Summa']
    pct_cols   = ['Alennus-%', 'Veroprosentti (%)']
    int_cols   = ['Määrä']

    for col in money_cols:
        df[col] = _clean_money_column(df[col])

    for col in pct_cols:
        # Convert '24' → 24.0
        df[col] = pd.to_numeric(df[col], errors='coerce')

    for col in int_cols:
        df[col] = pd.to_numeric(df[col], downcast='integer', errors='coerce')

    # Ensure identifiers stay as strings
    df['Y-tunnus']        = df['Y-tunnus'].astype(str)
    df['Yrityksen nimi']  = df['Yrityksen nimi'].astype(str)
    df['Tuotekoodi']      = df['Tuotekoodi'].astype(str)

    # Drop any completely empty rows
    df.dropna(how='all', inplace=True)

    return df

if __name__ == '__main__':
    # quick smoke-test
    path = '../data/netvisor_procountor_2024_2025.xlsx'
    df   = load_data(path)
    df   = clean_dataframe(df)
    print(df.head())
    print(df.dtypes)
