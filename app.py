"""
AGEL – Solar/Wind Power Forecasting Performance Overview
Main Streamlit Application
"""

import streamlit as st
import pandas as pd
import threading
import time

from config import (
    APP_NAME, DATA_REFRESH_DATE, PAGE_CONFIG, COLORS,
    MONTH_COLUMNS, CATEGORY_OPTIONS, PLANT_TYPES, SUB_TYPE_DESCRIPTIONS
)
from data import load_data, unpivot_months, filter_by_months, filter_data, get_khavda_data
from metrics import (
    calculate_total_avc, calculate_avc_by_dimension,
    calculate_avc_by_dimension_with_breakdown, calculate_agency_penalties,
    calculate_penalty_trend, calculate_site_penalties, get_agency_full_breakdown,
    get_portfolio_full_breakdown, calculate_weighted_penalty
)
from charts import (
    create_line_chart, create_bar_chart, create_site_bar_chart, 
    create_stacked_area_chart, create_capacity_timeline,
    create_site_scatter_plot, create_site_trend_chart,
    create_trend_chart_with_agency_styles, create_site_trend_chart_with_agency_styles
)
from ai import prepare_ai_context, get_gemini_response, MODEL_PRIMARY


# ============================================================
# Page Configuration
# ============================================================
st.set_page_config(**PAGE_CONFIG)


@st.cache_resource
def get_cached_image(image_path, **kwargs):
    """Load and cache images to prevent reloading on ogni rerun"""
    return image_path


# ============================================================
# Custom CSS Styling
# ============================================================
@st.cache_data
def apply_custom_css():
    # Calculate precise positions for dots on the slider track
    num_months = len(MONTH_COLUMNS)
    # Subtle blue dots (markers) tailored for ultra-thin track
    stops = [f"radial-gradient(circle at {i * 100 / (num_months - 1)}% 50%, rgba(3, 169, 244, 0.45) 1.8px, transparent 1.8px)" for i in range(num_months)]
    dots_background = ", ".join(stops)
    
    # New Blueish-White Palette
    line_color = "#F0F7FF"      # Blueish White
    selection_color = "#E1F5FE" # Light Blue shading
    accent_blue = "#03A9F4"     # Professional Blue for knobs
    slider_thickness = "2.5px"
    
    st.markdown(f"""
    <style>
        /* Import Google Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Global styles */
        .stApp {{
            background-color: {COLORS["background"]};
            font-family: 'Inter', sans-serif;
        }}
        
        /* Hide default header to reveal top border */
        header[data-testid="stHeader"] {{
            visibility: hidden;
            height: 0px;
        }}

        /* Hide image toolbar icons (fullscreen, download, etc.) */
        button[title="View fullscreen"] {{
            visibility: hidden;
            display: none;
        }}
        [data-testid="stImageHoverControls"] {{
            display: none !important;
        }}

        /* Main container - Bordered White Shell */
        .main .block-container {{
            padding: 2.5rem 3.5rem !important;
            margin-top: 1.2rem !important;
            margin-bottom: 3rem !important;
            border-radius: 20px !important;
            box-shadow: 0 12px 40px rgba(0,0,0,0.06) !important;
            border: 1px solid #E3F2FD !important;
            max-width: 1450px;
            background-color: #FFFFFF;
        }}
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {{
            color: {COLORS["text_primary"]} !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
        }}
        
        h1 {{
            font-size: 1.75rem ;
            margin-bottom: 0.5rem !important;
        }}
        
        h2 {{
            font-size: 1.45rem !important;
            margin-top: 1.6rem !important;
            margin-bottom: 0.8rem !important;
            padding-bottom: 0.5rem;
            position: relative;
        }}
        
        h3 {{
            font-size: 1.25rem !important;
            margin-top: 1.2rem !important;
            margin-bottom: 0.6rem !important;
        }}
        
        h4 {{
            font-size: 1.1rem !important;
            margin-top: 1rem !important;
            margin-bottom: 0.5rem !important;
            color: {COLORS["text_secondary"]} !important;
        }}
        
        /* Subtle divider for sections */
        hr {{
            margin: 1.4rem 0 !important;
            border: 0 !important;
            border-top: 2.5px solid {COLORS["border"]} !important;
        }}
        
        /* Metric cards */
        .metric-card {{
            background: {COLORS["card_bg"]};
            border-radius: 12px;
            padding: 1.75rem;
            box-shadow: 0 2px 12px rgba(30, 136, 229, 0.08);
            border: 2px solid {COLORS["border"]};
            text-align: center;
            transition: all 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(30, 136, 229, 0.12);
            border-color: {COLORS["primary"]};
        }}
        
        .metric-value {{
            font-size: 2.1rem;
            font-weight: 700;
            color: {COLORS["primary"]};
            margin: 0.6rem 0;
        }}
        
        .metric-label {{
            font-size: 0.95rem;
            color: {COLORS["text_secondary"]};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.7px;
        }}
        
        .metric-sublabel {{
            font-size: 0.75rem;
            color: {COLORS["text_secondary"]};
            opacity: 0.8;
        }}
        
        /* Info blocks */
        .info-block {{
            background: {COLORS["card_bg"]};
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 12px rgba(30, 136, 229, 0.08);
            border: 2px solid {COLORS["border"]};
            margin: 0.6rem 0;
            text-align: center;
            transition: all 0.3s ease;
        }}
        
        .info-block:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(30, 136, 229, 0.12);
            border-color: {COLORS["primary"]};
        }}
        
        .info-block-value {{
            font-size: 1.85rem;
            font-weight: 600;
            color: {COLORS["text_primary"]};
        }}
        
        .info-block-label {{
            font-size: 0.95rem;
            color: {COLORS["text_secondary"]};
            font-weight: 500;
        }}
        
        .info-block-percent {{
            font-size: 1.05rem;
            color: {COLORS["primary"]};
            font-weight: 600;
        }}
        
        /* Agency blocks with tooltip */
        .agency-block-wrapper {{
            position: relative;
            display: inline-block;
            width: 100%;
        }}
        
        .agency-block {{
            background: {COLORS["card_bg"]};
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            border: 2px solid {COLORS["border"]};
            min-height: 120px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 12px rgba(30, 136, 229, 0.08);
        }}
        
        .agency-block:hover {{
            transform: translateY(-4px);
            border-color: {COLORS["primary"]};
            box-shadow: 0 8px 24px rgba(30, 136, 229, 0.12);
        }}
        
        .agency-name {{
            font-size: 1.05rem;
            font-weight: 600;
            color: {COLORS["text_primary"]};
            margin-bottom: 0.6rem;
        }}
        
        .agency-avc {{
            font-size: 1.5rem;
            font-weight: 700;
            color: {COLORS["primary"]};
        }}
        
        .agency-percent {{
            font-size: 0.85rem;
            color: {COLORS["text_secondary"]};
            font-weight: 500;
        }}
        
        /* Hover tooltip popup */
        .tooltip-content {{
            visibility: hidden;
            opacity: 0;
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #FFFFFF;
            color: {COLORS["text_primary"]};
            padding: 1.25rem;
            border-radius: 12px;
            font-size: 1rem;
            white-space: nowrap;
            z-index: 1000;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            border: 1.5px solid {COLORS["border"]};
            margin-bottom: 15px;
            transition: opacity 0.2s ease, visibility 0.2s ease;
        }}
        
        .tooltip-content::after {{
            content: '';
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border-width: 8px;
            border-style: solid;
            border-color: #FFFFFF transparent transparent transparent;
        }}
        
        .agency-block-wrapper:hover .tooltip-content {{
            visibility: visible;
            opacity: 1;
        }}

        .tooltip-header {{
            font-weight: 700;
            font-size: 1.1rem;
            margin-bottom: 0.85rem;
            color: {COLORS["primary"]};
            border-bottom: 1px solid {COLORS["border"]};
            padding-bottom: 0.5rem;
        }}

        .tooltip-category {{
            margin-top: 0.85rem;
        }}
        
        .tooltip-category-label {{
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: {COLORS["text_secondary"]};
            margin-bottom: 0.35rem;
        }}
        
        .tooltip-row {{
            display: flex;
            justify-content: space-between;
            gap: 1.5rem;
            margin: 0.2rem 0;
        }}
        
        .tooltip-label {{
            color: {COLORS["text_secondary"]};
            font-weight: 500;
        }}
        
        .tooltip-value {{
            font-weight: 600;
            color: {COLORS["text_primary"]};
        }}
        
        /* Penalty blocks */
        .penalty-block {{
            background: {COLORS["card_bg"]};
            border-radius: 12px;
            padding: 1.25rem 1.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 2px solid {COLORS["border"]};
            margin: 0.4rem 0;
            box-shadow: 0 2px 12px rgba(30, 136, 229, 0.08);
            transition: all 0.3s ease;
        }}
        
        .penalty-block:hover {{
            transform: scale(1.02);
            border-color: {COLORS["primary"]};
            box-shadow: 0 4px 16px rgba(30, 136, 229, 0.12);
        }}
        
        .penalty-agency {{
            font-size: 1.15rem;
            font-weight: 600;
            color: {COLORS["text_primary"]};
        }}
        
        .penalty-value {{
            font-size: 1.35rem;
            font-weight: 700;
            color: {COLORS["primary"]};
        }}

        /* Highlight container for important sections */
        .highlight-container {{
            background: #F0F7FF;
            border: 1px solid {COLORS["primary"]};
            border-radius: 16px;
            padding: 1.5rem 2rem;
            margin: 1.5rem 0;
            box-shadow: inset 0 2px 4px rgba(30, 136, 229, 0.05);
        }}
        
        .highlight-container h3 {{
            margin-top: 0;
            margin-bottom: 1.25rem !important;
            color: {COLORS["primary"]} !important;
            font-size: 1.2rem !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .penalty-row-flex {{
            display: flex;
            gap: 1rem;
            justify-content: space-between;
            flex-wrap: wrap;
        }}
        
        .penalty-row-flex .agency-block-wrapper {{
            flex: 1;
            min-width: 200px;
        }}

        /* Large Penalty blocks refined (moderate font increase) */
        .penalty-block-large {{
            background: #FFFFFF;
            border-radius: 12px;
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 2px solid {COLORS["primary"]};
            margin: 0.5rem 0;
            box-shadow: 0 4px 12px rgba(30, 136, 229, 0.1);
            transition: all 0.3s ease;
        }}

        .penalty-block-large:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(30, 136, 229, 0.15);
        }}

        .penalty-agency-large {{
            font-size: 1.25rem;
            font-weight: 700;
            color: {COLORS["text_primary"]};
        }}

        .penalty-value-large {{
            font-size: 1.6rem;
            font-weight: 800;
            color: {COLORS["primary"]};
        }}
        
        /* Section styling */
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        
        /* Data refresh badge */
        .data-refresh {{
            background: {COLORS["accent"]};
            color: {COLORS["text_primary"]};
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        
        /* Expander styling */
        .streamlit-expanderHeader {{
            background: {COLORS["card_bg"]} !important;
            border-radius: 8px !important;
            border: 1px solid {COLORS["border"]} !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            color: {COLORS["text_primary"]} !important;
        }}
        
        /* Slider styling - Blueish White & Ultra Thin */
        .stSlider [data-baseweb="slider"] {{
            margin-top: 2rem;
            margin-bottom: 3.5rem;
        }}
        
        /* Main track (Inactive line) - Blueish White with rounded edges */
        .stSlider [data-baseweb="slider"] > div {{
            height: {slider_thickness} !important;
            background-color: {line_color} !important;
            border-radius: 10px !important;
            /* Precise month markers */
            background-image: {dots_background} !important;
            background-repeat: no-repeat !important;
            border: 1px solid rgba(0,0,0,0.03);
        }}
        
        /* Selection segment (Active shading) - Light Blue */
        .stSlider [data-baseweb="slider"] > div > div {{
            background-color: {selection_color} !important; 
            height: {slider_thickness} !important;
            border-radius: 10px !important;
            background-image: {dots_background} !important;
            background-repeat: no-repeat !important;
        }}
        
        /* Knob styling - Restored and Professional */
        .stSlider [data-baseweb="slider"] [role="slider"] {{
            width: 16px !important;
            height: 16px !important;
            background-color: #FFFFFF !important;
            border: 2.5px solid {accent_blue} !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1) !important;
            cursor: pointer !important;
            display: block !important; /* Ensure visibility */
        }}
        
        .stSlider [data-baseweb="slider"] [role="slider"]:hover {{
            transform: scale(1.15);
        }}

        /* Hide the redundant floating labels but keep the main track and knobs */
        .stSlider [data-baseweb="slider"] > div > div:not(:nth-child(2)) {{
            /* This targets labels hidden within the track container if any */
        }}
        
        /* Show month labels below the slider */
        .stSlider [data-baseweb="slider"] + div {{
            display: flex !important;
            visibility: visible !important;
            justify-content: space-between !important;
            padding-top: 22px !important;
            margin-left: 8px !important;  /* Match slider internal padding */
            margin-right: 8px !important; /* Match slider internal padding */
        }}
        
        /* Ensure labels are centered under dots */
        .stSlider [data-baseweb="slider"] + div div {{
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            color: {COLORS["text_secondary"]} !important;
            width: 0 !important;
            overflow: visible !important;
            display: flex !important;
            justify-content: center !important;
            white-space: nowrap !important;
        }}
        
        /* Keep first and last slightly adjusted for edges if needed */
        .stSlider [data-baseweb="slider"] + div div:first-child {{
            justify-content: flex-start !important;
        }}
        .stSlider [data-baseweb="slider"] + div div:last-child {{
            justify-content: flex-end !important;
        }}
        
        /* Professional Label on top only */
        .stSlider [data-testid="stWidgetLabel"] p {{
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            color: {COLORS["text_primary"]} !important;
            margin-bottom: 0px !important;
        }}
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {{
            background: {COLORS["card_bg"]};
            border-right: 1px solid {COLORS["border"]};
        }}
        
        section[data-testid="stSidebar"] h1 {{
            font-size: 1.25rem !important;
        }}
        
        /* Navigation */
        .nav-link {{
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin: 0.25rem 0;
            cursor: pointer;
            transition: background 0.2s ease;
        }}
        
        .nav-link:hover {{
            background: {COLORS["background"]};
        }}
        
        .nav-link.active {{
            background: {COLORS["primary"]};
            color: white;
        }}
        
        /* Hide Streamlit branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: {COLORS["card_bg"]};
            border-radius: 8px 8px 0 0;
            padding: 10px 20px;
            border: 1px solid {COLORS["border"]};
            border-bottom: none;
        }}
        
        .stTabs [data-baseweb="tab"] p {{
            font-size: 1.1rem !important;
            font-weight: 500 !important;
        }}

        .stTabs [aria-selected="true"] {{
            background-color: {COLORS["primary"]} !important;
            color: white !important;
        }}

        /* Chatbot Interface Styling */
        .chat-container {{
            background: #FFFFFF;
            border-radius: 16px;
            border: 1.5px solid {COLORS["border"]};
            padding: 1.5rem;
            margin-top: 1rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        }}

        .chat-message {{
            padding: 1.1rem 1.4rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            line-height: 1.55;
            font-size: 1.05rem;
            position: relative;
        }}

        .user-message {{
            background-color: {COLORS["background"]};
            color: {COLORS["text_primary"]};
            border-bottom-right-radius: 2px;
            margin-left: 2rem;
            border: 1px solid {COLORS["border"]};
        }}

        .assistant-message {{
            background-color: #F0F7FF;
            color: {COLORS["text_primary"]};
            border-bottom-left-radius: 2px;
            margin-right: 2rem;
            border: 1px solid rgba(30, 136, 229, 0.1);
        }}

        .starter-question {{
            display: inline-block;
            padding: 0.5rem 1rem;
            background: #FFFFFF;
            border: 1px solid {COLORS["primary"]};
            color: {COLORS["primary"]};
            border-radius: 20px;
            font-size: 0.85rem;
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 500;
        }}

        .starter-question:hover {{
            background: {COLORS["primary"]};
            color: #FFFFFF;
            box-shadow: 0 4px 12px rgba(30, 136, 229, 0.2);
        }}

        .follow-up-container {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px dashed {COLORS["border"]};
        }}

        /* Alignment Fix for AI Assistant Icon and Headers */
        [data-testid="stChatMessage"] h1, 
        [data-testid="stChatMessage"] h2, 
        [data-testid="stChatMessage"] h3,
        [data-testid="stChatMessage"] p:first-child {{
            margin-top: 0px !important;
            padding-top: 0px !important;
        }}
        
        /* Ensure vertical alignment with avatar */
        [data-testid="stChatMessage"] {{
            display: flex;
            align-items: flex-start;
        }}
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# UI Components
# ============================================================
def render_metric_card(value: str, label: str, sublabel: str = ""):
    """Render a metric card"""
    sublabel_html = f'<div class="metric-sublabel">{sublabel}</div>' if sublabel else ""
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {sublabel_html}
        </div>
    """, unsafe_allow_html=True)


def render_info_block(value: str, label: str, percent: str = ""):
    """Render an info block with optional percentage"""
    percent_html = f'<span class="info-block-percent">({percent}%)</span>' if percent else ""
    st.markdown(f"""
        <div class="info-block">
            <div class="info-block-label">{label}</div>
            <div class="info-block-value">{value} {percent_html}</div>
        </div>
    """, unsafe_allow_html=True)


def get_breakdown_tooltip_html(name: str, breakdown_data: dict) -> str:
    """Generate tooltip HTML for portfolio breakdown"""
    if not breakdown_data:
        return ""
        
    sections = []
    labels = {
        "Plant_Type": "Plant Type Split",
        "Access_Type": "Access Type Split",
        "Transmission_Type": "Transmission Type Split"
    }
    
    header_title = name if "Portfolio" in name else f"{name} Portfolio"
    sections.append(f'<div class="tooltip-header">{header_title}</div>')
    
    for dim in ["Plant_Type", "Access_Type", "Transmission_Type"]:
        data = breakdown_data.get(dim)
        if not data: continue
        
        dim_html = f'<div class="tooltip-category">'
        dim_html += f'<div class="tooltip-category-label">{labels.get(dim, dim)}</div>'
        for sub_type, vals in data.items():
            if vals["AVC_MW"] > 0:
                dim_html += (
                    f'<div class="tooltip-row">'
                    f'<span class="tooltip-label">{sub_type}</span>'
                    f'<span class="tooltip-value">{vals["AVC_MW"]:,.0f} MW ({vals["Percentage"]}%)</span>'
                    f'</div>'
                )
        dim_html += '</div>'
        sections.append(dim_html)
        
    return f'<div class="tooltip-content">{"".join(sections)}</div>'


def render_agency_block(name: str, avc: float, percent: float, tooltip_data: dict = None):
    """Render an agency block with hover tooltip popup"""
    tooltip_html = get_breakdown_tooltip_html(name, tooltip_data)
    
    st.markdown(f"""
        <div class="agency-block-wrapper">
            {tooltip_html}
            <div class="agency-block">
                <div class="agency-name">{name}</div>
                <div class="agency-avc">{avc:,.0f} MW</div>
                <div class="agency-percent">{percent:.1f}%</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_penalty_row(agencies_df: pd.DataFrame, df: pd.DataFrame, title: str = "", is_large: bool = False, precalculated_breakdowns: dict = None):
    """Render a row of penalty blocks for agencies with hover breakdown"""
    
    if is_large:
        # Use single HTML block for highlighter to include title
        blocks_html = []
        for _, row in agencies_df.iterrows():
            agency_name = row['Forecasting_Agency']
            penalty = row["Weighted_Penalty"]
            color = COLORS["success"]
            
            tooltip_data = precalculated_breakdowns.get(agency_name) if precalculated_breakdowns else get_agency_full_breakdown(df, agency_name)
            tooltip_html = get_breakdown_tooltip_html(agency_name, tooltip_data)
            
            blocks_html.append(f"""
                <div class="agency-block-wrapper">
                    {tooltip_html}
                    <div class="penalty-block-large">
                        <span class="penalty-agency-large">{agency_name}</span>
                        <span class="penalty-value-large" style="color: {color}">{penalty:.2f}</span>
                    </div>
                </div>
            """)
        
        title_html = f"<h3>{title}</h3>" if title else ""
        joined_blocks = "".join(blocks_html).replace("\n", "").strip()
        st.markdown(f'<div class="highlight-container">{title_html}<div class="penalty-row-flex">{joined_blocks}</div></div>', unsafe_allow_html=True)
        
    else:
        # Standard rendering for smaller sections
        if title:
            st.markdown(f"### {title}")
            
        cols = st.columns(len(agencies_df))
        for idx, (_, row) in enumerate(agencies_df.iterrows()):
            agency_name = row['Forecasting_Agency']
            with cols[idx]:
                penalty = row["Weighted_Penalty"]
                color = COLORS["success"]
                
                tooltip_data = precalculated_breakdowns.get(agency_name) if precalculated_breakdowns else get_agency_full_breakdown(df, agency_name)
                tooltip_html = get_breakdown_tooltip_html(agency_name, tooltip_data)
                
                st.markdown(f"""
                    <div class="agency-block-wrapper">
                        {tooltip_html}
                        <div class="penalty-block">
                            <span class="penalty-agency">{agency_name}</span>
                            <span class="penalty-value" style="color: {color}">{penalty:.2f}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)


def render_combined_penalty_section(df: pd.DataFrame, portfolio_perf: pd.DataFrame, agency_penalties: pd.DataFrame, precalculated_breakdowns: dict = None):
    """Render both portfolio and agency penalties in a single highlight container"""
    
    # 1. Overall Portfolio Block
    portfolio_blocks = []
    if not portfolio_perf.empty:
        penalty = portfolio_perf["Weighted_Penalty"].iloc[0]
        name = "Overall Portfolio"
        tooltip_data = precalculated_breakdowns.get(name) if precalculated_breakdowns else get_portfolio_full_breakdown(df)
        tooltip_html = get_breakdown_tooltip_html(name, tooltip_data)
        
        portfolio_blocks.append(f"""
            <div class="agency-block-wrapper" style="flex: 1 1 100%;">
                {tooltip_html}
                <div class="penalty-block-large">
                    <span class="penalty-agency-large">{name}</span>
                    <span class="penalty-value-large" style="color: {COLORS['success']}">{penalty:.2f}</span>
                </div>
            </div>
        """)

    # 2. Agency Blocks
    agency_blocks = []
    if not agency_penalties.empty:
        for _, row in agency_penalties.iterrows():
            agency_name = row['Forecasting_Agency']
            penalty = row["Weighted_Penalty"]
            color = COLORS["success"]
            
            tooltip_data = precalculated_breakdowns.get(agency_name) if precalculated_breakdowns else get_agency_full_breakdown(df, agency_name)
            tooltip_html = get_breakdown_tooltip_html(agency_name, tooltip_data)
            
            agency_blocks.append(f"""
                <div class="agency-block-wrapper">
                    {tooltip_html}
                    <div class="penalty-block-large">
                        <span class="penalty-agency-large">{agency_name}</span>
                        <span class="penalty-value-large" style="color: {color}">{penalty:.2f}</span>
                    </div>
                </div>
            """)

    # Construct HTML
    portfolio_title_html = '<h3 style="margin-top: 0 !important;">Overall Portfolio Penalty</h3>' if portfolio_blocks else ""
    agency_title_html = '<h3 style="margin-top: 5rem !important;">Agency Penalties</h3>' if agency_blocks else ""
    
    joined_portfolio = "".join(portfolio_blocks).replace("\n", "")
    joined_agencies = "".join(agency_blocks).replace("\n", "")
    
    st.markdown(f"""
        <div class="highlight-container">
            {portfolio_title_html}
            <div class="penalty-row-flex">
                {joined_portfolio}
            </div>
            {agency_title_html}
            <div class="penalty-row-flex">
                {joined_agencies}
            </div>
        </div>
    """, unsafe_allow_html=True)



# ============================================================
# Page: Home
# ============================================================
def render_home_page(df: pd.DataFrame, df_long: pd.DataFrame, agency_breakdowns: dict = None):
    """Render the main home page"""
    
    # -------- Section 1: Portfolio Overview --------
    col1, col2 = st.columns([3, 1])
    
    with col1:
        total_avc = calculate_total_avc(df)
        render_metric_card(f"{total_avc:,.0f} MW", "Total Portfolio AVC")
    
    with col2:
        st.markdown(f"""
            <div class="data-refresh">
                Data last refreshed: {DATA_REFRESH_DATE}
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Plant Type Distribution
    avc_by_plant = calculate_avc_by_dimension(df, "Plant_Type")
    cols = st.columns(len(avc_by_plant))
    
    for idx, (_, row) in enumerate(avc_by_plant.iterrows()):
        with cols[idx]:
            render_info_block(
                f"{row['AVC_MW']:,.0f} MW",
                row["Plant_Type"],
                f"{row['Percentage']:.1f}"
            )
    
    st.markdown("---")
    
    # -------- Section 2: Portfolio Split by Forecasting Agencies --------
    st.markdown("## Portfolio Split by Forecasting Agencies")
    
    agency_data = calculate_avc_by_dimension(df, "Forecasting_Agency")
    
    cols = st.columns(len(agency_data))
    for idx, (_, row) in enumerate(agency_data.iterrows()):
        agency_name = row["Forecasting_Agency"]
        with cols[idx]:
            # Get full breakdown for agencies
            tooltip_data = get_agency_full_breakdown(df, agency_name)
            render_agency_block(
                agency_name,
                row["AVC_MW"],
                row["Percentage"],
                tooltip_data
            )
    
    st.markdown("---")
    
    # -------- Section 3: Structural Portfolio Splits (Collapsed) --------
    with st.expander("Portfolio split by Region, Access Type and Transmission type", expanded=False):
        # By Region
        st.markdown("### By Region")
        region_data = calculate_avc_by_dimension_with_breakdown(df, "Region", "Plant_Type")
        cols = st.columns(len(region_data))
        for idx, (_, row) in enumerate(region_data.iterrows()):
            with cols[idx]:
                # Simple plant type breakdown for non-agency blocks
                tooltip = {pt: {"AVC_MW": row[pt], "Percentage": round((row[pt]/row["AVC_MW"]*100),1)} 
                          for pt in PLANT_TYPES if pt in row and row[pt] > 0}
                render_agency_block(row["Region"], row["AVC_MW"], row["Percentage"], {"Plant_Type": tooltip})
        
        st.markdown("")
        
        # By Transmission Type
        st.markdown("### By Transmission Type")
        trans_data = calculate_avc_by_dimension_with_breakdown(df, "Transmission_Type", "Plant_Type")
        cols = st.columns(len(trans_data))
        for idx, (_, row) in enumerate(trans_data.iterrows()):
            with cols[idx]:
                tooltip = {pt: {"AVC_MW": row[pt], "Percentage": round((row[pt]/row["AVC_MW"]*100),1)} 
                          for pt in PLANT_TYPES if pt in row and row[pt] > 0}
                render_agency_block(row["Transmission_Type"], row["AVC_MW"], row["Percentage"], {"Plant_Type": tooltip})
        
        st.markdown("")
        
        # By Access Type
        st.markdown("### By Access Type")
        access_data = calculate_avc_by_dimension_with_breakdown(df, "Access_Type", "Plant_Type")
        cols = st.columns(len(access_data))
        for idx, (_, row) in enumerate(access_data.iterrows()):
            with cols[idx]:
                tooltip = {pt: {"AVC_MW": row[pt], "Percentage": round((row[pt]/row["AVC_MW"]*100),1)} 
                          for pt in PLANT_TYPES if pt in row and row[pt] > 0}
                render_agency_block(row["Access_Type"], row["AVC_MW"], row["Percentage"], {"Plant_Type": tooltip})
    
    st.markdown("---")
    
    # -------- Section 4: Forecast Penalty Analysis --------
    st.markdown("## Forecast Penalty Analysis")
    st.markdown("*Performance is shown as **ps/kWh** (paisa per unit generated). **Lower values indicate better performance**.*")
    
    # Month slider
    month_range = st.select_slider(
        "Select Month Range",
        options=MONTH_COLUMNS,
        value=(MONTH_COLUMNS[0], MONTH_COLUMNS[-1]),
        key="home_month_slider"
    )
    
    # Filter data by selected months
    df_filtered = filter_by_months(df_long, month_range[0], month_range[1])
    
    # Calculate Overall Portfolio Penalty and Agency Penalties
    portfolio_perf = calculate_weighted_penalty(df_filtered)
    agency_penalties = calculate_agency_penalties(df_filtered)
    render_combined_penalty_section(df, portfolio_perf, agency_penalties, precalculated_breakdowns=agency_breakdowns)
    
    st.markdown("")
    
    # Category selector
    selected_category = st.radio(
        "Split by Category",
        options=list(CATEGORY_OPTIONS.keys()),
        index=1,
        horizontal=True,
        key="home_category"
    )
    
    category_col = CATEGORY_OPTIONS[selected_category]
    category_values = df_filtered[category_col].dropna().unique().tolist()
    
    for cat_value in category_values:
        st.markdown(f"### {cat_value}")
        # Display helper description in a beautiful italicized format
        if cat_value in SUB_TYPE_DESCRIPTIONS:
            st.markdown(f"*{SUB_TYPE_DESCRIPTIONS[cat_value]}*")
            
        cat_penalties = calculate_agency_penalties(df_filtered, category_col, cat_value)
        if not cat_penalties.empty:
            render_penalty_row(cat_penalties, df, precalculated_breakdowns=agency_breakdowns)
    
    st.markdown("---")
    
    # -------- Section 5: Agency Penalty Trends --------
    st.markdown("## Agency-wise Penalty Trends")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        plant_types = st.multiselect(
            "Plant Type",
            options=df["Plant_Type"].dropna().unique().tolist(),
            default=df["Plant_Type"].dropna().unique().tolist(),
            key="trend_plant_type"
        )
    
    with col2:
        access_types = st.multiselect(
            "Access Type",
            options=df["Access_Type"].dropna().unique().tolist(),
            default=df["Access_Type"].dropna().unique().tolist(),
            key="trend_access_type"
        )
    
    with col3:
        trans_types = st.multiselect(
            "Transmission Type",
            options=df["Transmission_Type"].dropna().unique().tolist(),
            default=df["Transmission_Type"].dropna().unique().tolist(),
            key="trend_trans_type"
        )
    
    # Calculate trend
    filters = {
        "Plant_Type": plant_types,
        "Access_Type": access_types,
        "Transmission_Type": trans_types
    }
    
    trend_data = calculate_penalty_trend(df_filtered, filters)
    
    if not trend_data.empty:
        fig = create_line_chart(trend_data, title="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")
    
    st.markdown("---")
    
    # -------- Gemini AI Assistant --------
    home_starters = [
        "What is the overall trend of AVC-weighted Penalty (ps/kWh) across the portfolio?",
        "How do penalties compare between STOA and LTA?",
        "Which Forecasting Agency has the highest average penalty?"
    ]
    # Build dynamic filter context for AI
    home_filters = {"Plant_Type": plant_types, "Access_Type": access_types, "Transmission_Type": trans_types}
    home_context = f"Home Page — Overall AGEL Portfolio | Month Range: {month_range[0]} to {month_range[1]}, Category Split: {selected_category}, Active Filters: {home_filters}"
    st.session_state["ai_context_home"] = home_context
    render_ai_assistant(df, df_long, page_id="home", starters=home_starters)


@st.fragment
def render_ai_assistant(df: pd.DataFrame, df_long: pd.DataFrame, page_id: str = "default", starters: list = None):
    """Render the AI Assistant chatbot interface with background thread resilience and custom starters"""
    
    def safe_rerun():
        """Attempt fragment-scoped rerun, fall back to full rerun."""
        try:
            st.rerun(scope="fragment")
        except Exception:
            st.rerun()
    
    if starters is None:
        starters = ["Why is AGEL performing better?", "STOA (DAM) impact?", "Trend of Manikaran", "Solar vs Wind"]
    
    history_key = f"chat_history_{page_id}"
    confirm_clear_key = f"confirm_clear_{page_id}"
    status_key = f"ai_status_{page_id}"
    context_key = f"ai_context_{page_id}"

    # Get the latest context from session state (updated by the parent page)
    # This bypasses st.fragment argument snapshotting
    page_context = st.session_state.get(context_key, "Overall Portfolio")

    # Initialize chat history
    if history_key not in st.session_state:
        st.session_state[history_key] = []
        
    if status_key not in st.session_state:
        st.session_state[status_key] = None
    
    # Initialize context directly on this run so it sees fresh data every render
    current_ai_context = prepare_ai_context(df, df_long)
    
    # Callbacks for safe state updates without st.rerun()
    def trigger_clear():
        st.session_state[confirm_clear_key] = True

    def confirm_clear():
        st.session_state[history_key] = []
        st.session_state[confirm_clear_key] = False

    def cancel_clear():
        st.session_state[confirm_clear_key] = False

    # Header Actions
    head_col1, head_col2 = st.columns([5, 1])
    with head_col1:
        st.markdown('<h2 style="margin-bottom: 0px; padding-bottom: 0px; margin-top: 0px;">AI Assistant</h2>', unsafe_allow_html=True)
    with head_col2:
        st.button("🗑️ Clear", use_container_width=True, help="Clear history", key=f"clear_btn_{page_id}", on_click=trigger_clear)
            
    if st.session_state.get(confirm_clear_key):
        st.warning("⚠️ Clear all conversation history for this page?")
        c1, c2 = st.columns(2)
        c1.button("Yes, Clear", use_container_width=True, type="primary", key=f"confirm_yes_{page_id}", on_click=confirm_clear)
        c2.button("No, Keep", use_container_width=True, key=f"confirm_no_{page_id}", on_click=cancel_clear)

    st.markdown('<div style="margin-top: -20px; margin-bottom: 15px;">', unsafe_allow_html=True)
    st.caption("Ask Gemini about trends, comparisons, or impacts. Analysis continues in background if you switch pages.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Suggestions logic
    current_suggestions = starters
    history = st.session_state[history_key]
    
    if history:
        last_msg = history[-1]
        if last_msg["role"] == "assistant" and "PENDING..." not in last_msg["content"]:
            # Robust parsing for follow-up questions using regex
            import re
            content = last_msg["content"]
            # Find all instances of FOLLOW_UP: followed by text until the end of line or next tag
            found_questions = re.findall(r"FOLLOW_UP:\s*(.*?)(?=FOLLOW_UP:|$)", content, re.DOTALL)
            follow_ups = [q.strip() for q in found_questions if q.strip()]
            if follow_ups: 
                current_suggestions = follow_ups[:3] # Limit to top 3 to keep UI clean

    # Create a container for the chat history
    # This allows us to process the input logic BEFORE rendering the messages,
    # solving the "swallowed first prompt" issue without needing st.rerun().
    history_container = st.container()
    
    # Check if we are currently waiting for a response
    is_busy = any(msg["role"] == "assistant" and msg["content"] == "PENDING..." for msg in history)

    # Auto-scroll to chat section when actively interacting (prevents scroll-jump to middle)
    if is_busy:
        import streamlit.components.v1 as components
        components.html(
            """
            <script>
                // Scroll the parent Streamlit page to the bottom where the chat is
                const mainDoc = window.parent.document;
                const chatAnchors = mainDoc.querySelectorAll('[data-testid="stChatInput"]');
                if (chatAnchors.length > 0) {
                    chatAnchors[chatAnchors.length - 1].scrollIntoView({behavior: 'smooth', block: 'end'});
                } else {
                    // Fallback: scroll to bottom of main content
                    const mainContent = mainDoc.querySelector('[data-testid="stAppViewContainer"]');
                    if (mainContent) { mainContent.scrollTop = mainContent.scrollHeight; }
                }
            </script>
            """,
            height=0
        )

    # Chat Input / Suggestions handle
    def start_request(prompt):
        # 1. Add user message
        st.session_state[history_key].append({"role": "user", "content": prompt})
        # 2. Add pending assistant message with start timestamp
        st.session_state[history_key].append({
            "role": "assistant", 
            "content": "PENDING...",
            "start_time": time.time()
        })
        st.session_state[status_key] = "Initializing Analysis..."
        safe_rerun()

    # Chat Input
    user_input = st.chat_input("Ask a question about performance...", disabled=is_busy, key=f"chat_input_{page_id}")
    if user_input:
        start_request(user_input)

    # Suggestions row
    if not is_busy and current_suggestions:
        cols = st.columns(len(current_suggestions))
        for i, choice in enumerate(current_suggestions):
            if cols[i].button(choice, key=f"suggest_{i}_{len(history)}", use_container_width=True):
                start_request(choice)

    # Render History inside the container
    with history_container:
        # Refresh history from session state in case it was just modified
        history = st.session_state[history_key]
        pending_idx = -1
        
        for i, msg in enumerate(history):
            content = msg["content"]
            if msg["role"] == "assistant" and content == "PENDING...":
                pending_idx = i
                # The stream logic happens below
                continue
                
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant":
                    display_text = content
                    clean_content = display_text.split("FOLLOW_UP:")[0].strip()
                    st.markdown(clean_content)
                    
                    # Check for errors and show retry button
                    if "### Error" in clean_content or "ERROR:" in clean_content:
                        def retry_query(idx=i):
                            st.session_state[history_key] = st.session_state[history_key][:idx]
                            st.session_state[history_key].append({"role": "assistant", "content": "PENDING..."})
                        st.button("🔄 Retry Query", key=f"retry_{i}_{len(history)}", on_click=retry_query)
                    
                    # Show Metrics (Model Name & Performance)
                    metrics_cols = st.columns([1, 1])
                    if "model" in msg and msg.get("model"):
                        metrics_cols[0].caption(f"Generated by: {msg['model']}")
                    if "duration" in msg:
                        metrics_cols[1].markdown(f'<p style="color: #9e9e9e; font-size: 0.8rem; text-align: right; margin-top: 5px;">Query completed in {msg["duration"]:.1f}s</p>', unsafe_allow_html=True)
                else:
                    st.markdown(content)
                    
        # Process Pending Message if it exists
        if pending_idx != -1:
            with st.chat_message("assistant"):
                status_placeholder = st.empty()
                stream_placeholder = st.empty()
                
                def update_status(text):
                    status_placeholder.markdown(f"*{text}*")
                
                try:
                    # Stream the response correctly
                    prompt = history[pending_idx - 1]["content"] if pending_idx > 0 else ""
                    # Create generator
                    response_stream = get_gemini_response(
                        prompt, 
                        current_ai_context, 
                        history[:pending_idx], 
                        page_context=page_context,
                        status_callback=update_status
                    )
                    
                    # Read from stream and write directly
                    final_response_text = ""
                    for chunk in response_stream:
                        final_response_text += chunk
                        stream_placeholder.markdown(final_response_text)
                    
                    status_placeholder.empty()
                    
                    # Calculate duration
                    start_time = history[pending_idx].get("start_time", time.time())
                    duration = time.time() - start_time
                    
                    # Clean up layout explicitly by clearing the PENDING message in state
                    # and writing the final string to history.
                    st.session_state[history_key][pending_idx] = {
                        "role": "assistant",
                        "content": final_response_text,
                        "model": MODEL_PRIMARY,
                        "duration": duration
                    }
                    safe_rerun()
                except Exception as e:
                    import traceback
                    import logging
                    logging.error(f"Error streaming response: {traceback.format_exc()}")
                    st.session_state[history_key][pending_idx] = {
                        "role": "assistant", 
                        "content": f"### Error\nAn error occurred during streaming: `{str(e)}`.",
                        "model": "error"
                    }
                    safe_rerun()
    
    # End of AI Assistant Render


# ============================================================
# Page: Khavda
# ============================================================
def render_khavda_page(df: pd.DataFrame, df_long: pd.DataFrame):
    """Render the Khavda page (Region=WR, Agency=AGEL)"""
    
    # Filter for Khavda scope
    df_khavda = get_khavda_data(df)
    df_khavda_long = df_long[(df_long["Region"] == "WR") & (df_long["Forecasting_Agency"] == "AGEL")]
    
    st.markdown("## Portfolio split")
    st.caption("Region: WR | Forecasting Agency: AGEL")
    
    # 1.2 First row total portfolio AVC
    total_avc = calculate_total_avc(df_khavda)
    render_metric_card(f"{total_avc:,.0f} MW", "Total Portfolio AVC")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 1.3 Portfolio split by plant type
    st.markdown("### By plant type")
    avc_by_plant = calculate_avc_by_dimension(df_khavda, "Plant_Type")
    cols = st.columns(len(avc_by_plant))
    for idx, (_, row) in enumerate(avc_by_plant.iterrows()):
        with cols[idx]:
            render_info_block(
                f"{row['AVC_MW']:,.0f} MW",
                row["Plant_Type"],
                f"{row['Percentage']:.1f}"
            )
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 1.4 Portfolio split by Access type
    st.markdown("### By Access type")
    avc_by_access = calculate_avc_by_dimension(df_khavda, "Access_Type")
    cols = st.columns(len(avc_by_access))
    for idx, (_, row) in enumerate(avc_by_access.iterrows()):
        with cols[idx]:
            render_info_block(
                f"{row['AVC_MW']:,.0f} MW",
                row["Access_Type"],
                f"{row['Percentage']:.1f}"
            )
    
    st.markdown("---")
    
    # Capacity Addition Timeline
    st.markdown("## Capacity Addition Timeline")
    
    if not df_khavda_long.empty:
        fig = create_capacity_timeline(df_khavda_long)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No capacity timeline data available.")
    
    st.markdown("---")
    
    
    # -------- Section: Penalty Analysis --------
    st.markdown("## Penalty Analysis")
    st.markdown("*Performance is shown as **ps/kWh** (paisa per unit generated). **Lower values indicate better performance**.*")
    
    month_range = st.select_slider(
        "Select Month Range",
        options=MONTH_COLUMNS,
        value=(MONTH_COLUMNS[0], MONTH_COLUMNS[-1]),
        key="khavda_month_slider"
    )
    
    df_khavda_filtered = filter_by_months(df_khavda_long, month_range[0], month_range[1])
    
    # 3. Aggregated analysis (Subsection)
    st.markdown("### Aggregated analysis")
    
    # 3.1 Overall Performance
    st.markdown("#### Overall Performance")
    
    # Overall Performance
    overall_perf = calculate_weighted_penalty(df_khavda_filtered)
    if not overall_perf.empty:
        penalty_val = overall_perf["Weighted_Penalty"].iloc[0]
        render_metric_card(f"{penalty_val:.2f} ps/kWh", "Overall Portfolio Penalty", "Weighted average across sites & months")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3.2 By plant type
    st.markdown("#### By plant type")
    pt_perf = calculate_weighted_penalty(df_khavda_filtered, group_by=["Plant_Type"])
    if not pt_perf.empty:
        # Sort by AVC_MW descending to match Section 1
        pt_perf = pt_perf.sort_values("AVC_MW", ascending=False)
        cols = st.columns(len(pt_perf))
        for idx, (_, row) in enumerate(pt_perf.iterrows()):
            with cols[idx]:
                render_info_block(
                    f"{row['Weighted_Penalty']:.2f} ps/kWh",
                    row["Plant_Type"]
                )
                
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3.3 By Access type
    st.markdown("#### By Access type")
    at_perf = calculate_weighted_penalty(df_khavda_filtered, group_by=["Access_Type"])
    if not at_perf.empty:
        # Sort by AVC_MW descending to match Section 1
        at_perf = at_perf.sort_values("AVC_MW", ascending=False)
        cols = st.columns(len(at_perf))
        for idx, (_, row) in enumerate(at_perf.iterrows()):
            with cols[idx]:
                render_info_block(
                    f"{row['Weighted_Penalty']:.2f} ps/kWh",
                    row["Access_Type"]
                )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3.4 Month-on-Month Performance Trend
    st.markdown("#### Month-on-Month Performance Trend")
    
    trend_category = st.radio(
        "Select Trend Category",
        options=["Overall", "Plant Type", "Access Type"],
        horizontal=True,
        key="khavda_trend_cat"
    )
    
    # Calculate trend data
    if trend_category == "Overall":
        # For overall, we want one line representing the entire Khavda portfolio
        # We can use create_line_chart but we need to calculate weighted penalty per month
        trend_df = df_khavda_filtered.groupby("Month").apply(
            lambda x: (x["Penalty_ps_per_kwh"] * x["AVC_MW"]).sum() / x["AVC_MW"].sum()
        ).reset_index(name="Penalty")
        trend_df["Category"] = "Overall Portfolio"
        fig = create_line_chart(trend_df, color="Category", title="")
    else:
        # Grouped by Plant Type or Access Type
        group_col = "Plant_Type" if trend_category == "Plant Type" else "Access_Type"
        trend_df = df_khavda_filtered.groupby([group_col, "Month"]).apply(
            lambda x: (x["Penalty_ps_per_kwh"] * x["AVC_MW"]).sum() / x["AVC_MW"].sum()
            if x["AVC_MW"].sum() > 0 else 0
        ).reset_index(name="Penalty")
        fig = create_line_chart(trend_df, color=group_col, title="")
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # 4. Site-level analysis
    st.markdown("### Site-level analysis")
    
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        plant_filter = st.multiselect(
            "Filter by Plant Type",
            options=df_khavda["Plant_Type"].dropna().unique().tolist(),
            default=df_khavda["Plant_Type"].dropna().unique().tolist(),
            key="khavda_plant_filter"
        )
    
    with col_f2:
        access_filter = st.multiselect(
            "Filter by Access Type",
            options=df_khavda["Access_Type"].dropna().unique().tolist(),
            default=df_khavda["Access_Type"].dropna().unique().tolist(),
            key="khavda_access_filter"
        )
    
    # Filter the data for site-level analysis
    df_khavda_site_filtered = df_khavda_filtered.copy()
    if plant_filter:
        df_khavda_site_filtered = df_khavda_site_filtered[df_khavda_site_filtered["Plant_Type"].isin(plant_filter)]
    if access_filter:
        df_khavda_site_filtered = df_khavda_site_filtered[df_khavda_site_filtered["Access_Type"].isin(access_filter)]

    # 4.1 Overall Performance
    st.markdown("#### Overall Performance")
    site_penalties = calculate_site_penalties(df_khavda_site_filtered, {}) # Filters already applied
    
    if not site_penalties.empty:
        fig_scatter = create_site_scatter_plot(site_penalties)
        st.plotly_chart(fig_scatter, use_container_width=True, key="khavda_site_scatter")
    else:
        st.info("No data available for the selected filters.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4.2 Month-on-Month Performance Trend
    st.markdown("#### Month-on-Month Performance Trend")
    with st.expander("Click to expand", expanded=False):
        if not df_khavda_site_filtered.empty:
            fig_trend = create_site_trend_chart(df_khavda_site_filtered)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No trend data available for the selected filters.")

    st.markdown("---")
    # -------- Gemini AI Assistant --------
    khavda_starters = [
        "Compare the penalty performance across PSS groups by extracting the PSS identifier (e.g., PSS 1, PSS 2) from the Site_Name column.",
        "How does AVC and its trend vary across different PSS of Khavda?",
        "What are the top 3 penalty sites under each PSS?"
    ]
    # Build dynamic filter context for AI
    khavda_filters = {"Region": ["WR"], "Forecasting_Agency": ["AGEL"], "Plant_Type": plant_filter, "Access_Type": access_filter}
    khavda_context = f"Khavda | Month Range: {month_range[0]} to {month_range[1]}, Active Filters: {khavda_filters}"
    st.session_state["ai_context_khavda"] = khavda_context
    render_ai_assistant(df, df_long, page_id="khavda", starters=khavda_starters)


# ============================================================
# Page: Deep Dive
# ============================================================
def render_deep_dive_page(df: pd.DataFrame, df_long: pd.DataFrame, agency_breakdowns: dict = None):
    """Render the Deep Dive analysis page"""
    
    st.markdown("## Filters")
    
    # Hierarchical filtering logic
    # Start with all data
    df_filtered = df_long.copy()
    
    # 1. First Row: Month Range (Full Width)
    month_range = st.select_slider(
        "Month Range",
        options=MONTH_COLUMNS,
        value=(MONTH_COLUMNS[0], MONTH_COLUMNS[-1]),
        key="dd_month_slider"
    )
    # Apply month filter immediately
    df_filtered = filter_by_months(df_filtered, month_range[0], month_range[1])
        
    # 2. Second Row: Region, Plant Type, Transmission Type
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    
    with row2_col1:
        region_options = sorted(df_filtered["Region"].dropna().unique().tolist())
        regions = st.multiselect(
            "Region",
            options=region_options,
            default=region_options,
            key="dd_region"
        )
        if regions:
            df_filtered = df_filtered[df_filtered["Region"].isin(regions)]

    with row2_col2:
        pt_options = sorted(df_filtered["Plant_Type"].dropna().unique().tolist())
        plant_types = st.multiselect(
            "Plant Type",
            options=pt_options,
            default=pt_options,
            key="dd_plant"
        )
        if plant_types:
            df_filtered = df_filtered[df_filtered["Plant_Type"].isin(plant_types)]
            
    with row2_col3:
        trans_options = sorted(df_filtered["Transmission_Type"].dropna().unique().tolist())
        trans_types = st.multiselect(
            "Transmission Type",
            options=trans_options,
            default=trans_options,
            key="dd_trans"
        )
        if trans_types:
            df_filtered = df_filtered[df_filtered["Transmission_Type"].isin(trans_types)]
            
    # 3. Third Row: Access Type and Forecasting Agency
    row3_col1, row3_col2 = st.columns([1, 2])
    
    with row3_col1:
        access_options = sorted(df_filtered["Access_Type"].dropna().unique().tolist())
        access_types = st.multiselect(
            "Access Type",
            options=access_options,
            default=access_options,
            key="dd_access"
        )
        if access_types:
            df_filtered = df_filtered[df_filtered["Access_Type"].isin(access_types)]

    with row3_col2:
        agency_options = sorted(df_filtered["Forecasting_Agency"].dropna().unique().tolist())
        agencies = st.multiselect(
            "Forecasting Agency",
            options=agency_options,
            default=agency_options,
            key="dd_agency"
        )
        if agencies:
            df_filtered = df_filtered[df_filtered["Forecasting_Agency"].isin(agencies)]

    st.caption("Note: If no options are selected for a filter, all options will be considered.")

    st.markdown("---")
    st.markdown("## Forecast Penalty Analysis")
    st.markdown("*Performance is shown as **ps/kWh** (paisa per unit generated). **Lower values indicate better performance**.*")
    
    # Agency Penalties highlighted
    if not df_filtered.empty:
        portfolio_perf = calculate_weighted_penalty(df_filtered)
        agency_penalties = calculate_agency_penalties(df_filtered)
        render_combined_penalty_section(df, portfolio_perf, agency_penalties, precalculated_breakdowns=agency_breakdowns)
    else:
        st.info("No data available for the selected filters.")
    
    
    # Category-Based Breakdown
    #st.markdown("## Category-Based Breakdown")
    
    selected_category = st.radio(
        "Split by Category",
        options=list(CATEGORY_OPTIONS.keys()),
        index=1,
        horizontal=True,
        key="dd_category"
    )
    
    category_col = CATEGORY_OPTIONS[selected_category]
    category_values = df_filtered[category_col].dropna().unique().tolist()
    
    for cat_value in category_values:
        st.markdown(f"### {cat_value}")
        # Display helper description in a beautiful italicized format
        if cat_value in SUB_TYPE_DESCRIPTIONS:
            st.markdown(f"*{SUB_TYPE_DESCRIPTIONS[cat_value]}*")
            
        cat_penalties = calculate_agency_penalties(df_filtered, category_col, cat_value)
        if not cat_penalties.empty:
            render_penalty_row(cat_penalties, df, precalculated_breakdowns=agency_breakdowns)
    
    st.markdown("---")
    
    # Agency Trends
    st.markdown("## Agency-wise Penalty Trends")
    
    trend_data = calculate_penalty_trend(df_filtered, {})
    
    if not trend_data.empty:
        fig = create_line_chart(trend_data, title="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data available.")
    
    st.markdown("---")
    
    # Site-level analysis
    st.markdown("## Site-level analysis")
    
    # 4.1 Overall Performance
    st.markdown("#### Overall Performance")
    site_penalties = calculate_site_penalties(df_filtered, {}) # Filters already applied
    
    if not site_penalties.empty:
        # Pass color="Forecasting_Agency" to color by agency as requested
        fig_scatter = create_site_scatter_plot(site_penalties, color="Forecasting_Agency")
        st.plotly_chart(fig_scatter, use_container_width=True, key="dd_site_scatter")
    else:
        st.info("No data available for the selected filters.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 4.2 Month-on-Month Performance Trend by Site with Agency-based Line Styles
    st.markdown("#### Month-on-Month Performance Trend")
    with st.expander("Click to expand", expanded=False):
        st.markdown("*Line styles vary by Forecasting Agency: AGEL (solid), Energy Meteo (dash), Manikaran (dot), RE Connect (dashdot), Enercast (longdash)*")

        # Agency options constrained by the global filters applied above
        agency_options_site = sorted(df_filtered["Forecasting_Agency"].dropna().unique().tolist())
        selected_site_agencies = st.multiselect(
            "Forecasting Agency (site trend)",
            options=agency_options_site,
            default=agency_options_site,
            key="dd_site_trend_agency"
        )

        # If the user clears selection, treat it as all (consistent with global behavior)
        if not selected_site_agencies:
            selected_site_agencies = agency_options_site

        # Filter the df for the selected agencies
        df_site_trend = df_filtered[df_filtered["Forecasting_Agency"].isin(selected_site_agencies)] if not df_filtered.empty else df_filtered

        if not df_site_trend.empty:
            fig_site_trend = create_site_trend_chart_with_agency_styles(df_site_trend)
            st.plotly_chart(fig_site_trend, use_container_width=True)
        else:
            st.info("No trend data available for the selected filters.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Detailed Data View
    st.markdown("#### Detailed Data View")
    with st.expander("Click to expand", expanded=False):
        if not df_filtered.empty:
            # Prepare display data
            display_df = df_filtered[["Site_Name", "Forecasting_Agency", "Plant_Type", 
                                       "Region", "Access_Type", "Transmission_Type",
                                       "AVC_MW", "Month", "Penalty_ps_per_kwh"]].copy()
            display_df = display_df.sort_values(["Forecasting_Agency", "Site_Name", "Month"])
            
            st.dataframe(display_df, use_container_width=True, height=400)
            
            # Download buttons in columns
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                # Filtered Data
                csv_filtered = display_df.to_csv(index=False)
                st.download_button(
                    label="Download Filtered Data (CSV)",
                    data=csv_filtered,
                    file_name="penalty_data_filtered.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with btn_col2:
                # Unfiltered Data
                csv_full = df_long.to_csv(index=False)
                st.download_button(
                    label="Download Entire Dataset (CSV)",
                    data=csv_full,
                    file_name="penalty_data_unfiltered.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info("No data to display.")

    st.markdown("---")
    # -------- Gemini AI Assistant --------
    deep_dive_starters = [
        "Which forecasting agency performs best for Solar, Wind, and Hybrid individually?",
        "Suggest the best forecasting agency for different regions.",
        "What are the top 3 penalty sites under each forecasting agency?"
    ]
    # Build dynamic filter context for AI
    dd_filters = {"Region": regions, "Plant_Type": plant_types, "Transmission_Type": trans_types, "Access_Type": access_types, "Forecasting_Agency": agencies}
    dd_context = f"Comparison Deep Dive | Month Range: {month_range[0]} to {month_range[1]}, Active Filters: {dd_filters}"
    st.session_state["ai_context_deep_dive"] = dd_context
    render_ai_assistant(df, df_long, page_id="deep_dive", starters=deep_dive_starters)


@st.cache_data
def get_cached_breakdowns(df_master):
    """Pre-calculate and cache all agency breakdowns from master data"""
    agencies_list = df_master["Forecasting_Agency"].dropna().unique().tolist()
    breakdowns = {agency: get_agency_full_breakdown(df_master, agency) for agency in agencies_list}
    # Add overall portfolio breakdown
    breakdowns["Overall Portfolio"] = get_portfolio_full_breakdown(df_master)
    return breakdowns


# ============================================================
# Main Application
# ============================================================
def main():
    """Main application entry point"""
    
    # Apply custom CSS
    apply_custom_css()
    
    # Load data
    try:
        df = load_data()
        df_long = unpivot_months(df)
        
        # Pre-calculate breakdowns once for efficiency with caching
        agency_breakdowns = get_cached_breakdowns(df)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()
    
    # Sidebar Navigation
    with st.sidebar:
        st.markdown("# Navigation menu")
        # st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["Home", "Khavda (WR)", "Comparison Deep Dive"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Combined Portfolio Summary Section
        st.markdown("### Portfolio Summary")
        regions_list = ", ".join(sorted(df["Region"].dropna().unique().tolist()))
        plants_list = ", ".join(sorted(df["Plant_Type"].dropna().unique().tolist()))
        access_list = ", ".join(sorted(df["Access_Type"].dropna().unique().tolist()))
        trans_list = ", ".join(sorted(df["Transmission_Type"].dropna().unique().tolist()))
        
        st.markdown(f"""
        - **Total Capacity:** {calculate_total_avc(df):,.0f} MW ({len(df)} Sites)
        - **Regions:** {regions_list}
        - **Plant Types:** {plants_list}
        - **Access / Trans.:** {access_list} | {trans_list}
        - **Last Updated:** {DATA_REFRESH_DATE}
        """)

        st.markdown("---")
        st.markdown("### Glossary")
        st.markdown("""
        - **STOA:** Short-Term Open Access
        - **LTA:** Long-Term Agreement
        - **CTU:** Central Transmission Utility
        - **STU:** State Transmission Utility
        - **WR:** Western Region
        - **NR:** Northern Region
        - **SR:** Southern Region
        """)
        st.markdown("---")
        st.markdown("### Regional Grids of India")
        st.image(get_cached_image("regional_grids.png"), use_column_width=True)
    
    # Determine page title
    page_titles = {
        "Home": APP_NAME,
        "Khavda (WR)": "Khavda (WR) - Performance Overview",
        "Comparison Deep Dive": "Comparison Deep Dive"
    }
    current_title = page_titles.get(page, APP_NAME)

    # Top Logo and Page Title
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        st.image(get_cached_image("adani_logo.png"), width=200)
    with col2:
        st.markdown(f"<h1 style='text-align: center; margin-top: 2rem; font-size: 2.4rem;'>{current_title}</h1>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Render selected page
    if page == "Home":
        render_home_page(df, df_long, agency_breakdowns)
    elif page == "Khavda (WR)":
        render_khavda_page(df, df_long)
    elif page == "Comparison Deep Dive":
        # Pass breakdown context to Deep Dive for optimization
        render_deep_dive_page(df, df_long, agency_breakdowns)

if __name__ == "__main__":
    main()
