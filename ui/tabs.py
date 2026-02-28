"""
Analysis tabs component
"""
import streamlit as st
from ui.tab_pages.lap_data import render_lap_analysis_tab, render_data_export_tab
from ui.tab_pages.track_performance import render_sector_analysis_tab, render_speed_traces_tab
from ui.tab_pages.telemetry import render_telemetry_tab
from ui.tab_pages.position_tracking import render_position_tracking_tab
from ui.tab_pages.tyre_analysis import render_tyre_analysis_tab


def render_analysis_tabs(session):
    """Render all analysis tabs"""
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Lap Analysis",
        "Sector Times",
        "Telemetry",
        "Position Tracking",
        "Speed Traces",
        "Tyre Analysis",
        "Data Export"
    ])

    with tab1:
        render_lap_analysis_tab(session)

    with tab2:
        render_sector_analysis_tab(session)

    with tab3:
        render_telemetry_tab(session)

    with tab4:
        render_position_tracking_tab(session)

    with tab5:
        render_speed_traces_tab(session)

    with tab6:
        render_tyre_analysis_tab(session)

    with tab7:
        render_data_export_tab(session)
