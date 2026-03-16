"""
Charts and visualization module for AGEL Dashboard
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config import AGENCY_COLORS, COLORS, MONTH_ORDER, MONTH_COLUMNS


def create_line_chart(
    df: pd.DataFrame,
    x: str = "Month",
    y: str = "Penalty",
    color: str = "Forecasting_Agency",
    title: str = ""
) -> go.Figure:
    """Create a line chart for penalty trends"""
    if df.empty:
        return go.Figure()
    
    # Sort by month order
    df = df.copy()
    df["Month_Sort"] = df[x].map(MONTH_ORDER)
    df = df.sort_values("Month_Sort")
    
    # Dynamic month ordering based on data presence to reflect slider selection
    current_months = sorted(df[x].unique(), key=lambda m: MONTH_ORDER.get(m, 0))
    
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        markers=True,
        title=title,
        color_discrete_map=AGENCY_COLORS,
        category_orders={x: current_months}
    )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text_primary"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)"
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"]
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            title="Penalty (ps/kWh)"
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified"
    )
    
    fig.update_traces(
        line=dict(width=2.5),
        marker=dict(size=8)
    )
    
    return fig


def create_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: str = None,
    orientation: str = "v",
    show_values: bool = True
) -> go.Figure:
    """Create a bar chart"""
    if df.empty:
        return go.Figure()
    
    if orientation == "h":
        fig = px.bar(
            df,
            y=x,
            x=y,
            color=color,
            title=title,
            orientation="h",
            color_discrete_map=AGENCY_COLORS if color == "Forecasting_Agency" else None
        )
    else:
        fig = px.bar(
            df,
            x=x,
            y=y,
            color=color,
            title=title,
            color_discrete_map=AGENCY_COLORS if color == "Forecasting_Agency" else None
        )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text_primary"]),
        xaxis=dict(
            showgrid=False,
            linecolor=COLORS["border"]
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"]
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=color is not None
    )
    
    if show_values:
        fig.update_traces(textposition="outside", texttemplate="%{y:.2f}" if orientation == "v" else "%{x:.2f}")
    
    return fig


def create_site_bar_chart(
    df: pd.DataFrame,
    title: str = "Site-Level Performance"
) -> go.Figure:
    """Create a bar chart for site-level penalty performance"""
    if df.empty:
        return go.Figure()
    
    # Sort by penalty descending
    df = df.sort_values("Avg_Penalty", ascending=True)
    
    # Create custom hover text
    hover_text = df.apply(
        lambda row: f"<b>{row['Site_Name']}</b><br>"
                   f"Penalty: {row['Avg_Penalty']:.2f} ps/kWh<br>"
                   f"AVC: {row['AVC_MW']:.1f} MW<br>"
                   f"Type: {row['Plant_Type']}<br>"
                   f"Access: {row['Access_Type']}",
        axis=1
    )
    
    # Color by plant type
    color_map = {
        "Solar": COLORS["primary"],
        "Wind": COLORS["secondary"],
        "Hybrid": COLORS["accent"]
    }
    
    colors = df["Plant_Type"].map(color_map)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df["Site_Name"],
        x=df["Avg_Penalty"],
        orientation="h",
        marker_color=colors,
        hovertext=hover_text,
        hoverinfo="text"
    ))
    
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=11, color=COLORS["text_primary"]),
        xaxis=dict(
            title="Penalty (ps/kWh)",
            showgrid=True,
            gridcolor=COLORS["border"]
        ),
        yaxis=dict(
            showgrid=False,
            autorange="reversed"
        ),
        margin=dict(l=200, r=40, t=60, b=40),
        height=max(400, len(df) * 25)
    )
    
    return fig


def create_stacked_area_chart(
    df: pd.DataFrame,
    x: str = "Month",
    y: str = "AVC_MW",
    color: str = "Plant_Type",
    title: str = ""
) -> go.Figure:
    """Create a stacked area chart for capacity timeline"""
    if df.empty:
        return go.Figure()
    
    # Pivot for stacked area
    pivot_df = df.pivot_table(
        index=x,
        columns=color,
        values=y,
        aggfunc="sum",
        fill_value=0
    ).reset_index()
    
    # Sort by month order
    pivot_df["Month_Sort"] = pivot_df[x].map(MONTH_ORDER)
    pivot_df = pivot_df.sort_values("Month_Sort")
    
    fig = go.Figure()
    
    color_map = {
        "Solar": COLORS["primary"],
        "Wind": COLORS["secondary"],
        "Hybrid": COLORS["accent"]
    }
    
    for plant_type in ["Solar", "Wind", "Hybrid"]:
        if plant_type in pivot_df.columns:
            fig.add_trace(go.Scatter(
                x=pivot_df[x],
                y=pivot_df[plant_type],
                name=plant_type,
                mode="lines",
                stackgroup="one",
                fillcolor=color_map.get(plant_type, COLORS["primary"]),
                line=dict(width=0.5, color=color_map.get(plant_type, COLORS["primary"]))
            ))
    
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text_primary"]),
        xaxis=dict(
            showgrid=True,
            gridcolor=COLORS["border"],
            categoryorder="array",
            categoryarray=sorted(df[x].unique(), key=lambda m: MONTH_ORDER.get(m, 0))
        ),
        yaxis=dict(
            title="AVC (MW)",
            showgrid=True,
            gridcolor=COLORS["border"]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified"
    )
    
    return fig


def create_capacity_timeline(
    df_long: pd.DataFrame, 
    title: str = "", 
    color: COLORS["primary"] = "#1E88E5"
) -> go.Figure:
    """Create a horizontal milestone-style timeline for capacity additions with site details"""
    if df_long.empty:
        return go.Figure()
    
    # Sort months correctly
    months_in_data = sorted(df_long["Month"].unique(), key=lambda m: MONTH_ORDER.get(m, 99))
    
    # Identify sites and their first month
    site_first_month = df_long.groupby("Site_Name").agg({
        "Month": lambda x: sorted(x, key=lambda m: MONTH_ORDER.get(m, 99))[0],
        "Plant_Type": "first",
        "AVC_MW": "first"
    }).reset_index()
    
    # Aggregated capacity per month for the timeline points
    monthly_cap = df_long.groupby("Month")["AVC_MW"].sum().reset_index()
    monthly_cap["Month_Sort"] = monthly_cap["Month"].map(MONTH_ORDER)
    monthly_cap = monthly_cap.sort_values("Month_Sort")
    
    milestones = monthly_cap["Month"].tolist()
    total_caps = monthly_cap["AVC_MW"].tolist()
    
    # Create the figure
    fig = go.Figure()
    
    # Main horizontal baseline
    fig.add_trace(go.Scatter(
        x=milestones,
        y=[0] * len(milestones),
        mode="lines",
        line=dict(color=color, width=4),
        hoverinfo="skip",
        showlegend=False
    ))
    
    # Milestones (points)
    fig.add_trace(go.Scatter(
        x=milestones,
        y=[0] * len(milestones),
        mode="markers",
        marker=dict(
            color="white",
            size=18,
            line=dict(color=color, width=3)
        ),
        hoverinfo="skip",
        showlegend=False
    ))
    
    # 1. Add Month Labels (Always below)
    for i, month in enumerate(milestones):
        fig.add_annotation(
            x=month,
            y=-0.35, # Below the line
            text=f"<b>{month}</b>",
            showarrow=False,
            font=dict(size=13, color=COLORS["text_primary"]),
            yanchor="top"
        )
        # Total Capacity at that point (Always above)
        fig.add_annotation(
            x=month,
            y=0.35,
            text=f"Total: {total_caps[i]:,.0f} MW",
            showarrow=False,
            font=dict(size=11, color=COLORS["text_secondary"]),
            yanchor="bottom"
        )

    # 2. Identify Additions and place in gaps
    for i in range(1, len(milestones)):
        prev_month = milestones[i-1]
        curr_month = milestones[i]
        
        # Sites starting in curr_month
        additions = site_first_month[site_first_month["Month"] == curr_month]
        
        if not additions.empty:
            mid_x = i - 0.5 # Logical midpoint for categorical X
            
            # Group additions to show in a single block or multiple boxes
            # We'll split them if too many
            for idx, (_, row) in enumerate(additions.iterrows()):
                direction = 1 if idx % 2 == 0 else -1
                y_pos = 0.85 * direction
                
                # Connector line to midpoint
                fig.add_shape(
                    type="line",
                    x0=mid_x, y0=0,
                    x1=mid_x, y1=y_pos * 0.8,
                    line=dict(color=COLORS["accent"], width=1.5, dash="dot"),
                    xref="x", yref="y"
                )
                
                label = (
                    f"<b>{row['Site_Name']}</b><br>"
                    f"{row['Plant_Type']} | {row['AVC_MW']:,.1f} MW"
                )
                
                fig.add_annotation(
                    x=mid_x,
                    y=y_pos,
                    text=label,
                    showarrow=False,
                    bgcolor="rgba(255, 255, 255, 0.9)",
                    bordercolor=COLORS["primary"] if row['Plant_Type'] == 'Solar' else (COLORS["success"] if row['Plant_Type'] == 'Wind' else COLORS["warning"]),
                    borderwidth=1,
                    borderpad=6,
                    font=dict(size=10, color=COLORS["text_primary"]),
                    align="center",
                    yanchor="bottom" if direction == 1 else "top"
                )

    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-0.5, len(milestones) - 0.2]
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-2.2, 2.2]
        ),
        margin=dict(l=40, r=40, t=10, b=10),
        height=450,
        hovermode=False
    )
    
    return fig


def create_site_scatter_plot(
    df: pd.DataFrame,
    title: str = "",
    color: str = None
) -> go.Figure:
    """Create a scatter plot for site-level analysis (AVC vs Penalty)"""
    if df.empty:
        return go.Figure()
        
    # Standardize data types for hover
    df = df.copy()
    df["Month_Count"] = df["Month_Count"].astype(int)
        
    fig = px.scatter(
        df,
        x="AVC_MW",
        y="Avg_Penalty",
        size="Avg_Penalty",
        color=color,
        color_discrete_map=AGENCY_COLORS if color == "Forecasting_Agency" else None,
        hover_name="Site_Name",
        # Explicitly pass custom_data to ensure mapping in hovertemplate is accurate
        custom_data=["Month_Count", "Plant_Type", "Region", "Forecasting_Agency"],
        title=title
    )
    
    # Customize hover template using explicit customdata indices
    # customdata[0] -> Month_Count
    # customdata[1] -> Plant_Type
    # customdata[2] -> Region
    # customdata[3] -> Forecasting_Agency
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" +
                      "AVC: %{x:.1f} MW<br>" +
                      "Avg Penalty: %{y:.2f} ps/kWh<br>" +
                      "Averaged over: %{customdata[0]} months<br>" +
                      "Type: %{customdata[1]}<br>" +
                      "Region: %{customdata[2]}<br>" +
                      "Agency: %{customdata[3]}<extra></extra>",
        # Use sizemin to ensure bubbles never become invisible or too small to click,
        # while keeping the scaling relative to the data.
        marker=dict(sizemin=5)
    )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text_primary"]),
        xaxis=dict(
            title="AVC (MW)",
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"]
        ),
        yaxis=dict(
            title="Avg Penalty (ps/kWh)",
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"]
        ),
        margin=dict(l=40, r=40, t=40, b=40),
        showlegend=color is not None,
        # Increase size_max slightly to allow Plotly a better range for relative scaling
        # (Plotly default is 20, we'll set it to a healthy 40 to allow for contrast)
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Only apply uniform color if no color dimension is provided
    if color is None:
        fig.update_traces(
            marker=dict(
                opacity=0.7, 
                line=dict(width=1, color='White'),
                sizemin=5 # Ensure sizemin persists in this update as well
            ),
            marker_color=COLORS["primary"]
        )
    else:
        fig.update_traces(
            marker=dict(
                opacity=0.7, 
                line=dict(width=1, color='White'),
                sizemin=5 # Ensure sizemin persists in this update as well
            )
        )
    
    return fig


def create_site_trend_chart(
    df_long: pd.DataFrame,
    title: str = ""
) -> go.Figure:
    """Create a line chart for individual site performance trends"""
    if df_long.empty:
        return go.Figure()
        
    # Sort by month order
    df_long = df_long.copy()
    df_long["Month_Sort"] = df_long["Month"].map(MONTH_ORDER)
    df_long = df_long.sort_values(["Month_Sort", "Site_Name"])
    
    # Dynamic month ordering
    current_months = sorted(df_long["Month"].unique(), key=lambda m: MONTH_ORDER.get(m, 0))
    
    fig = px.line(
        df_long,
        x="Month",
        y="Penalty_ps_per_kwh",
        color="Site_Name",
        markers=True,
        title=title,
        category_orders={"Month": current_months}
    )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text_primary"]),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"]
        ),
        yaxis=dict(
            title="Penalty (ps/kWh)",
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"]
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2, # Push legend below
            xanchor="center",
            x=0.5
        ),
        hovermode="x unified",
        height=500
    )
    
    fig.update_traces(line=dict(width=2), marker=dict(size=6))
    
    return fig


def create_trend_chart_with_agency_styles(
    df: pd.DataFrame,
    title: str = "Month-on-Month Performance Trend"
) -> go.Figure:
    """
    Create a line chart for trend analysis with different line styles based on Forecasting_Agency.
    Each agency gets a unique line style (solid, dash, dot, dashdot, etc.).
    """
    if df.empty:
        return go.Figure()
    
    # Sort by month order
    df = df.copy()
    df["Month_Sort"] = df["Month"].map(MONTH_ORDER)
    df = df.sort_values(["Month_Sort", "Forecasting_Agency"])
    
    # Define line styles for different agencies
    line_styles = {
        "AGEL": "solid",
        "Energy Meteo": "dash",
        "Manikaran": "dot",
        "RE Connect": "dashdot",
        "Enercast": "longdash"
    }
    
    fig = go.Figure()
    
    # Get unique agencies and sort them
    agencies = sorted(df["Forecasting_Agency"].unique())
    
    # Add a trace for each agency with its corresponding line style
    for agency in agencies:
        agency_data = df[df["Forecasting_Agency"] == agency]
        
        # Get the line style for this agency
        line_style = line_styles.get(agency, "solid")
        
        fig.add_trace(go.Scatter(
            x=agency_data["Month"],
            y=agency_data["Penalty"],
            name=agency,
            mode="lines+markers",
            line=dict(
                color=AGENCY_COLORS.get(agency, COLORS["primary"]),
                width=2.5,
                dash=line_style
            ),
            marker=dict(
                size=8,
                color=AGENCY_COLORS.get(agency, COLORS["primary"])
            ),
            hovertemplate="<b>%{fullData.name}</b><br>Month: %{x}<br>Penalty: %{y:.2f} ps/kWh<extra></extra>"
        ))
    
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text_primary"]),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            categoryorder="array",
            categoryarray=sorted(df["Month"].unique(), key=lambda m: MONTH_ORDER.get(m, 0))
        ),
        yaxis=dict(
            title="Penalty (ps/kWh)",
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)"
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified"
    )
    
    return fig


def create_site_trend_chart_with_agency_styles(
    df_long: pd.DataFrame,
    title: str = "Month-on-Month Performance Trend by Site"
) -> go.Figure:
    """
    Create a line chart for individual site performance trends with different line styles based on Forecasting_Agency.
    Each site gets its own line, and the line style is determined by its forecasting agency.
    """
    if df_long.empty:
        return go.Figure()
    
    # Sort by month order
    df_long = df_long.copy()
    df_long["Month_Sort"] = df_long["Month"].map(MONTH_ORDER)
    df_long = df_long.sort_values(["Month_Sort", "Forecasting_Agency", "Site_Name"])
    
    # Define line styles for different agencies
    line_styles = {
        "AGEL": "solid",
        "Energy Meteo": "dash",
        "Manikaran": "dot",
        "RE Connect": "dashdot",
        "Enercast": "longdash"
    }
    
    fig = go.Figure()

    # Get unique sites
    sites = sorted(df_long["Site_Name"].unique())

    # Generate a distinct color for each site using Plotly qualitative palette
    palette = px.colors.qualitative.Plotly
    # If more sites than palette entries, cycle through palette
    site_colors = {site: palette[i % len(palette)] for i, site in enumerate(sites)}

    # Add a trace for each site with unique color and agency-based line style
    for site in sites:
        site_data = df_long[df_long["Site_Name"] == site]

        # Get agency for this site (should be consistent for all rows of this site)
        agency = site_data["Forecasting_Agency"].iloc[0] if not site_data.empty else "Unknown"

        # Get the line style for this agency
        line_style = line_styles.get(agency, "solid")

        fig.add_trace(go.Scatter(
            x=site_data["Month"],
            y=site_data["Penalty_ps_per_kwh"],
            name=site,
            mode="lines+markers",
            line=dict(
                color=site_colors.get(site, COLORS["primary"]),
                width=2.5,
                dash=line_style
            ),
            marker=dict(
                size=6,
                color=site_colors.get(site, COLORS["primary"])
            ),
            hovertemplate=("<b>%{fullData.name}</b><br>Month: %{x}<br>Penalty: %{y:.2f} ps/kWh<br>Agency: " + agency + "<extra></extra>")
        ))
    
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text_primary"]),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            categoryorder="array",
            categoryarray=sorted(df_long["Month"].unique(), key=lambda m: MONTH_ORDER.get(m, 0))
        ),
        yaxis=dict(
            title="Penalty (ps/kWh)",
            showgrid=True,
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"]
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255,255,255,0.8)",
            font=dict(size=10)
        ),
        margin=dict(l=40, r=200, t=60, b=40),
        hovermode="x unified",
        height=500
    )
    
    return fig
