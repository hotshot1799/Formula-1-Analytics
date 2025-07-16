"""
Session overview component
"""
import streamlit as st
from analysis_utils import format_session_info, get_season_indicator

def render_session_overview(session, stats):
    """Render session overview"""
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔄 Total Laps", stats.get('total_laps', 0))
    with col2:
        st.metric("🏎️ Drivers", stats.get('total_drivers', 0))
    with col3:
        st.metric("⚡ Fastest Lap", stats.get('fastest_lap_time', 'N/A'))
    with col4:
        st.metric("🏆 Fastest Driver", stats.get('fastest_lap_driver', 'N/A'))
    
    # Additional info
    info_text = format_session_info(stats)
    if info_text:
        st.markdown(info_text)
    
    # Season indicator
    current_year = st.session_state.get('year', 2024)
    indicator_text, indicator_type = get_season_indicator(current_year)
    
    if indicator_type == "success":
        st.success(indicator_text)
    else:
        st.info(indicator_text)