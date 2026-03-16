"""
Metrics and aggregation module for AGEL Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
from config import MONTH_COLUMNS, MONTH_ORDER


def calculate_total_avc(df: pd.DataFrame) -> float:
    """Calculate total portfolio AVC (MW)"""
    return df["AVC_MW"].sum()


@st.cache_data
def calculate_avc_by_dimension(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Calculate AVC grouped by a dimension with percentage share"""
    avc_grouped = df.groupby(dimension)["AVC_MW"].sum().reset_index()
    total_avc = avc_grouped["AVC_MW"].sum()
    avc_grouped["Percentage"] = (avc_grouped["AVC_MW"] / total_avc * 100).round(1)
    avc_grouped = avc_grouped.sort_values("AVC_MW", ascending=False)
    return avc_grouped


@st.cache_data
def calculate_avc_by_dimension_with_breakdown(
    df: pd.DataFrame, 
    dimension: str, 
    breakdown_dim: str = "Plant_Type"
) -> pd.DataFrame:
    """Calculate AVC by dimension with plant type breakdown for tooltips"""
    # Main aggregation
    main_agg = calculate_avc_by_dimension(df, dimension)
    
    # Breakdown aggregation
    breakdown = df.groupby([dimension, breakdown_dim])["AVC_MW"].sum().unstack(fill_value=0)
    breakdown = breakdown.reset_index()
    
    # Merge
    result = main_agg.merge(breakdown, on=dimension, how="left")
    return result


@st.cache_data
def get_agency_full_breakdown(df: pd.DataFrame, agency_name: str) -> dict:
    """Calculate all breakdowns for a specific agency"""
    agency_df = df[df["Forecasting_Agency"] == agency_name]
    if agency_df.empty:
        return {}
    
    total_avc = agency_df["AVC_MW"].sum()
    
    breakdown = {}
    dimensions = ["Plant_Type", "Access_Type", "Transmission_Type"]
    
    for dim in dimensions:
        dim_agg = agency_df.groupby(dim)["AVC_MW"].sum().reset_index()
        dim_agg["Percentage"] = (dim_agg["AVC_MW"] / total_avc * 100).round(1)
        # Convert to dict
        breakdown[dim] = dim_agg.set_index(dim).to_dict(orient="index")
        
    return breakdown


@st.cache_data
def get_portfolio_full_breakdown(df: pd.DataFrame) -> dict:
    """Calculate all breakdowns for the entire portfolio"""
    if df.empty:
        return {}
    
    total_avc = df["AVC_MW"].sum()
    
    breakdown = {}
    dimensions = ["Plant_Type", "Access_Type", "Transmission_Type"]
    
    for dim in dimensions:
        dim_agg = df.groupby(dim)["AVC_MW"].sum().reset_index()
        dim_agg["Percentage"] = (dim_agg["AVC_MW"] / total_avc * 100).round(1)
        # Convert to dict
        breakdown[dim] = dim_agg.set_index(dim).to_dict(orient="index")
        
    return breakdown


def _aggregate_monthly_weighted_penalty(df: pd.DataFrame, group_by: list) -> pd.DataFrame:
    """Internal helper to calculate monthly weighted penalties"""
    temp_df = df.copy()
    temp_df["weighted_penalty"] = temp_df["Penalty_ps_per_kwh"] * temp_df["AVC_MW"]
    
    monthly = temp_df.groupby(group_by + ["Month"]).agg({
        "weighted_penalty": "sum",
        "AVC_MW": "sum"
    }).reset_index()
    
    monthly["Monthly_Penalty"] = monthly["weighted_penalty"] / monthly["AVC_MW"]
    return monthly


def calculate_weighted_penalty(
    df_long: pd.DataFrame,
    group_by: list = None
) -> pd.DataFrame:
    """
    Calculate AVC-weighted average penalty across sites,
    then simple average across months
    """
    if group_by is None:
        group_by = []
    
    if group_by:
        monthly = _aggregate_monthly_weighted_penalty(df_long, group_by)
        
        # Simple average across months for each group
        result = monthly.groupby(group_by).agg({
            "Monthly_Penalty": "mean",
            "AVC_MW": "first"  # AVC should be same across months for a group
        }).reset_index()
        
        result = result.rename(columns={"Monthly_Penalty": "Weighted_Penalty"})
    else:
        # Overall portfolio penalty
        monthly = _aggregate_monthly_weighted_penalty(df_long, [])
        
        # Simple average across months
        result = pd.DataFrame({
            "Weighted_Penalty": [monthly["Monthly_Penalty"].mean()],
            "Total_AVC": [df_long["AVC_MW"].sum() / df_long["Month"].nunique()]
        })
    
    return result


@st.cache_data
def calculate_agency_penalties(
    df_long: pd.DataFrame,
    category_filter: str = None,
    category_value: str = None
) -> pd.DataFrame:
    """Calculate penalty for each agency, optionally filtered by category"""
    df_filtered = df_long
    
    if category_filter and category_value:
        df_filtered = df_filtered[df_filtered[category_filter] == category_value]
    
    if df_filtered.empty:
        return pd.DataFrame(columns=["Forecasting_Agency", "Weighted_Penalty", "AVC_MW"])
    
    monthly = _aggregate_monthly_weighted_penalty(df_filtered, ["Forecasting_Agency"])
    
    # Then average across months
    result = monthly.groupby("Forecasting_Agency").agg({
        "Monthly_Penalty": "mean",
        "AVC_MW": "sum"
    }).reset_index()
    
    result = result.rename(columns={"Monthly_Penalty": "Weighted_Penalty"})
    result = result.sort_values("Weighted_Penalty", ascending=True)
    
    # Divide AVC by number of months to get average
    num_months = df_filtered["Month"].nunique()
    result["AVC_MW"] = result["AVC_MW"] / num_months if num_months > 0 else result["AVC_MW"]
    
    return result


@st.cache_data
def calculate_penalty_trend(
    df_long: pd.DataFrame,
    filters: dict = None
) -> pd.DataFrame:
    """Calculate monthly penalty trend by agency"""
    df_filtered = df_long.copy()
    
    if filters:
        for col, values in filters.items():
            if values and col in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[col].isin(values)]
    
    if df_filtered.empty:
        return pd.DataFrame()
    
    # Calculate weighted penalty by agency and month
    df_filtered["weighted_penalty"] = df_filtered["Penalty_ps_per_kwh"] * df_filtered["AVC_MW"]
    
    result = df_filtered.groupby(["Forecasting_Agency", "Month"]).agg({
        "weighted_penalty": "sum",
        "AVC_MW": "sum"
    }).reset_index()
    
    result["Penalty"] = result["weighted_penalty"] / result["AVC_MW"]
    
    # Sort by month order
    result["Month_Order"] = result["Month"].map(MONTH_ORDER)
    result = result.sort_values(["Month_Order", "Forecasting_Agency"])
    
    return result[["Forecasting_Agency", "Month", "Penalty", "AVC_MW"]]


def calculate_site_penalties(
    df_long: pd.DataFrame,
    filters: dict = None
) -> pd.DataFrame:
    """Calculate average penalty by site, excluding those with no data in selected frame"""
    df_filtered = df_long.copy()
    
    # 1. Apply additional filters (Plant Type, Access Type, etc.)
    if filters:
        for col, values in filters.items():
            if values and col in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[col].isin(values)]
    
    # 2. Drop any rows where penalty is NaN (ensures count is accurate)
    df_filtered = df_filtered.dropna(subset=["Penalty_ps_per_kwh"])
    
    if df_filtered.empty:
        return pd.DataFrame()
    
    # 3. Average across selected months for each site, and record count of months
    result = df_filtered.groupby(["Site_Name", "AVC_MW", "Plant_Type", "Access_Type", "Forecasting_Agency", "Region"]).agg({
        "Penalty_ps_per_kwh": ["mean", "count"]
    }).reset_index()
    
    # Flatten multi-index columns
    result.columns = ["Site_Name", "AVC_MW", "Plant_Type", "Access_Type", "Forecasting_Agency", "Region", "Avg_Penalty", "Month_Count"]
    
    # 4. Final safety check: drop sites that might have ended up with NaN results or 0 count
    result = result.dropna(subset=["Avg_Penalty"])
    result = result[result["Month_Count"] > 0]
    
    result = result.sort_values("Avg_Penalty", ascending=False)
    
    return result
