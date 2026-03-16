"""
Configuration file for AGEL Solar/Wind Power Forecasting Performance Dashboard
"""

import pandas as pd
import os
from datetime import datetime

# Application metadata
APP_NAME = "Performance Overview of Generation forecasting"

# Data file
DATA_FILE = "penalty_data_upto_jan.csv"
# Column mappings (raw -> standardized)
COLUMN_MAPPING = {
    "Plant Name": "Site_Name",
    "Forecasting Agency": "Forecasting_Agency",
    "Transmission": "Transmission_Type",
    "Region": "Region",
    "AVC (MW)": "AVC_MW",
    "Plant Type": "Plant_Type",
    "Access Type": "Access_Type"
}

# Function to get dynamic values from CSV
def get_dynamic_config(file_path):
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"], "17 January 2026"
            
        # Read header only to get columns
        df_header = pd.read_csv(file_path, nrows=0)
        cols = df_header.columns.tolist()
        
        # Valid month abbreviations
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        # Extract columns that are month names
        extracted_months = []
        for c in cols:
            # Check if column name matches any month name (exact or prefix like Apr-25)
            if any(m in c for m in month_names):
                # Exclude known metadata columns
                if c not in ["Forecasting Agency", "Plant Name", "Transmission", "Region", "Plant Type", "Access Type"]:
                    extracted_months.append(c)
        
        # Refresh date: last modified time of the data file
        mtime = os.path.getmtime(file_path)
        refresh_date = datetime.fromtimestamp(mtime).strftime("%d %B %Y")
        
        return extracted_months, refresh_date
    except Exception:
        return ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"], "17 January 2026"

MONTH_COLUMNS, DATA_REFRESH_DATE = get_dynamic_config(DATA_FILE)
MONTH_ORDER = {month: i for i, month in enumerate(MONTH_COLUMNS)}
PRIMARY_METRIC = "Penalty (ps/kWh)"

# Category options for Section 4
CATEGORY_OPTIONS = {
    "Plant Type": "Plant_Type",
    "Access Type": "Access_Type", 
    "Transmission Type": "Transmission_Type"
}

# Plant types
PLANT_TYPES = ["Solar", "Wind", "Hybrid"]

# Descriptions for each sub-type
SUB_TYPE_DESCRIPTIONS = {
    "Solar": "Generally lower and more stable penalties due to the highly predictable nature of solar cycles.",
    "Wind": "Higher penalties are common due to high variability and sudden ramps in wind speed.",
    "Hybrid": "Balanced penalties as solar stability partially offsets wind variability.",
    "STOA": "Higher penalties expected as forecasts must be submitted 24h in advance with no revisions allowed.",
    "LTA": "Lower penalties as intraday revisions allow schedules to be adjusted to real-time trends.",
    "CTU": "Centrally operated with a typically more stringent and standardized penalty mechanism.",
    "STU": "Mechanism and rates vary by state, often differing in flexibility from the CTU framework."
} 

# Color palette - Light bluish theme
COLORS = {
    "primary": "#1E88E5",
    "secondary": "#42A5F5",
    "accent": "#90CAF9",
    "background": "#F9FBFF",
    "card_bg": "#FFFFFF",
    "text_primary": "#1A237E",
    "text_secondary": "#5C6BC0",
    "border": "#E3F2FD",
    "success": "#4CAF50",
    "warning": "#FF9800",
    "error": "#F44336",
    # Agency colors
    "AGEL": "#1565C0",
    "Energy Meteo": "#2E7D32",
    "Manikaran": "#7B1FA2",
    "RE Connect": "#C62828",
    "Enercast": "#00838F"
}

# Chart colors for agencies
AGENCY_COLORS = {
    "AGEL": "#1565C0",
    "Energy Meteo": "#2E7D32", 
    "Manikaran": "#7B1FA2",
    "RE Connect": "#C62828",
    "Enercast": "#00838F"
}

# Page configuration
PAGE_CONFIG = {
    "page_title": APP_NAME,
    "page_icon": "adani_logo.png",
    "layout": "wide",
    "initial_sidebar_state": "collapsed"
}
