"""
Analysis tabs component
"""
import streamlit as st
from ui.tabs.lap_analysis import render_lap_analysis_tab
from ui.tabs.sector_analysis import render_sector_analysis_tab
from ui.tabs.telemetry import render_telemetry_tab
from ui.tabs.position_tracking import render_position_tracking_tab
from ui.tabs.speed_traces import render_speed_traces_tab
from ui.tabs.data_export import render_data_export_tab

def render_analysis_tabs(session):
    """Render all analysis tabs"""
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Lap Analysis", 
        "⏱️ Sector Times", 
        "📈 Telemetry", 
        "🏁 Position Tracking",
        "🎯 Speed Traces",
        "📋 Data Export"
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
        render_data_export_tab(session)