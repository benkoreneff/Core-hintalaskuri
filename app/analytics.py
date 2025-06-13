# app/analytics.py

import pandas as pd


def monthly_totals(
    df: pd.DataFrame,
    amount_col: str = 'Summa'
) -> pd.DataFrame:
    """
    Group cleaned data by company, program, and month, summing up `amount_col`.
    Returns columns: Y-tunnus, Yrityksen nimi, Ohjelmisto, Kuukausi, MonthlySum.
    """
    return (
        df
        .groupby(
            ['Y-tunnus', 'Yrityksen nimi', 'Ohjelmisto', 'Kuukausi'],
            as_index=False
        )[amount_col]
        .sum()
        .rename(columns={amount_col: 'MonthlySum'})
    )

def compute_company_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
     Summarize monthly sums for one program/company:
      - Mean over all months
      - Mean, std, CV over last 3 months
      - Mean, std, CV over last 12 months
    """
    mt = monthly_totals(df)

    def summarize(group: pd.DataFrame) -> pd.Series:
        # Sort by month
        g = group.sort_values("Kuukausi")
        start = g["Kuukausi"].min()
        end = g["Kuukausi"].max()
        last3 = g["MonthlySum"].tail(3)
        last12 = g["MonthlySum"].tail(12)

        # ── approximate seasonality via rolling-mean detrending ──
        # window=12, center so we capture mid‐year trend, allow min_periods=6
        rolling_mean = g["MonthlySum"].rolling(window=12, center=True, min_periods=6).mean()
        seasonal_comp = g["MonthlySum"] - rolling_mean
        seasonal_amp = seasonal_comp.max() - seasonal_comp.min()
        # use the mean of the rolling trend where available, else overall mean
        trend_est = rolling_mean.mean() if pd.notna(rolling_mean.mean()) else g["MonthlySum"].mean()
        seasonal_ratio = seasonal_amp / (trend_est or 1)

        # ── simple growth ratio ──
        growth_ratio = last3.mean() / (last12.mean() or 1)

        return pd.Series({
            "Program":   g["Ohjelmisto"].iat[0],
            "DateRange": f"{start.strftime('%b-%y')} to {end.strftime('%b-%y')}",
            "AvgAll": g["MonthlySum"].mean(),
            "Avg3Mo": last3.mean(),
            "Avg12Mo": last12.mean(),
            "Std3Mo": last3.std(ddof=0),  # population std dev
            "Std12Mo": last12.std(ddof=0),
            "CV3Mo": last3.std(ddof=0) / (last3.mean() or 1),
            "CV12Mo": last12.std(ddof=0) / (last12.mean() or 1),
            "GrowthRatio": growth_ratio,
            "Seasonality": seasonal_ratio,
        })

    summary = (
            mt[
            ['Y-tunnus', 'Yrityksen nimi', 'Ohjelmisto', 'Kuukausi', 'MonthlySum']
            ]
            .groupby(
            ['Y-tunnus', 'Yrityksen nimi', 'Ohjelmisto'],
            as_index=False
            )
            .apply(summarize)
            .reset_index(drop=True)
           )

    # Drop the extra 'Ohjelmisto' index column since it's now in 'Program'
    summary = summary.drop(columns=['Ohjelmisto'], errors='ignore')
    return summary
