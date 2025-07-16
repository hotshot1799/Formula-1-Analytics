"""
Header component
"""
import streamlit as st
from data_loader import get_available_years

def render_header():
    """Render page header"""
    st.title("🏎️ Formula 1 Analytics Dashboard")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("*Advanced F1 telemetry and race analysis*")
    with col2:
        available_years = get_available_years()
        latest_year = max(available_years) if available_years else 2024
        if latest_year >= 2025:
            st.success(f"🏁 **{latest_year} LIVE**")
        else:
            st.info(f"📚 **{latest_year}**")
    with col3:
        if st.button("🔄 Refresh", help="Clear cache"):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")