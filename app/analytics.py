
import pandas as pd

def monthly_totals(df: pd.DataFrame, amount_col: str = 'Summa') -> pd.DataFrame:
    """
    Group cleaned data by company and month, summing up the 'Summa' for each.
    """
    return (
        df
        .groupby(['Y-tunnus', 'Yrityksen nimi', 'Kuukausi'], as_index=False)[amount_col]
        .sum()
        .rename(columns={amount_col: 'MonthlySum'})
    )

def compute_company_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each company, compute:
      - AvgMo   = mean of all months
      - Avg3Mo  = mean of the last 3 months
      - Avg12Mo = mean of the last 12 months
    Returns one row per company.
    """
    mt = monthly_totals(df)

    def summarize(group: pd.DataFrame) -> pd.Series:
        g = group.sort_values('Kuukausi')
        return pd.Series({
            'AvgMo': g['MonthlySum'].mean(),
            'Avg3Mo': g['MonthlySum'].tail(3).mean(),
            'Avg12Mo': g['MonthlySum'].tail(12).mean()
        })

    summary = (
        mt
        .groupby(['Y-tunnus', 'Yrityksen nimi'])
        .apply(summarize)
        .reset_index()
    )
    return summary
