"""
Data loading and transformation module for AGEL Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
from config import COLUMN_MAPPING, MONTH_COLUMNS, DATA_FILE


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load and preprocess the penalty data from CSV"""
    df = pd.read_csv(DATA_FILE)
    
    # Rename columns to standardized names
    df = df.rename(columns=COLUMN_MAPPING)
    
    # Clean up the data
    df = df.dropna(subset=["Forecasting_Agency"])
    
    # Ensure AVC_MW is numeric
    df["AVC_MW"] = pd.to_numeric(df["AVC_MW"], errors="coerce")
    df = df.dropna(subset=["AVC_MW"])
    df = df[df["AVC_MW"] > 0]
    
    # Convert month columns to numeric
    for month in MONTH_COLUMNS:
        if month in df.columns:
            df[month] = pd.to_numeric(df[month], errors="coerce")
    
    # Drop YTD column if present
    if "YTD" in df.columns:
        df = df.drop(columns=["YTD"])
    
    return df


@st.cache_data
def unpivot_months(df: pd.DataFrame) -> pd.DataFrame:
    """
    Unpivot monthly penalty columns into Month and Penalty_ps_per_kwh columns
    """
    id_vars = [col for col in df.columns if col not in MONTH_COLUMNS]
    
    df_melted = pd.melt(
        df,
        id_vars=id_vars,
        value_vars=MONTH_COLUMNS,
        var_name="Month",
        value_name="Penalty_ps_per_kwh"
    )
    
    # Remove rows with NaN penalty values
    df_melted = df_melted.dropna(subset=["Penalty_ps_per_kwh"])
    
    return df_melted


def get_wide_format(df: pd.DataFrame) -> pd.DataFrame:
    """Return data in wide format (original with month columns)"""
    return df.copy()


def filter_by_months(df_long: pd.DataFrame, start_month: str, end_month: str) -> pd.DataFrame:
    """Filter long-format data by month range"""
    from config import MONTH_ORDER
    
    start_idx = MONTH_ORDER.get(start_month, 0)
    end_idx = MONTH_ORDER.get(end_month, len(MONTH_COLUMNS) - 1)
    
    valid_months = MONTH_COLUMNS[start_idx:end_idx + 1]
    return df_long[df_long["Month"].isin(valid_months)]


def filter_data(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Apply multiple filters to the dataframe"""
    df_filtered = df.copy()
    
    for column, values in filters.items():
        if values and column in df_filtered.columns:
            if isinstance(values, list):
                df_filtered = df_filtered[df_filtered[column].isin(values)]
            else:
                df_filtered = df_filtered[df_filtered[column] == values]
    
    return df_filtered


def get_khavda_data(df: pd.DataFrame) -> pd.DataFrame:
    """Get data for Khavda page (Region=WR, Forecasting_Agency=AGEL)"""
    return df[(df["Region"] == "WR") & (df["Forecasting_Agency"] == "AGEL")]
