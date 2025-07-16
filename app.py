"""
F1 Analytics Dashboard - Streamlined Main App
Clean, fast, and modular
"""
import streamlit as st
from ui.page_setup import setup_page
from ui.header import render_header
from ui.sidebar import render_sidebar
from ui.welcome import render_welcome_screen
from ui.session_overview import render_session_overview
from ui.tabs import render_analysis_tabs
from data_loader import get_session_stats

def main():
    """Main application - clean and simple"""
    # Setup
    setup_page()
    render_header()
    
    # Sidebar
    year, event, session_type, events = render_sidebar()
    
    # Main content - ALWAYS show latest race analysis first
    render_welcome_screen()
    
    # If user has loaded a specific session, show detailed analysis below
    if 'session' in st.session_state:
        st.markdown("---")
        st.markdown("## 🔬 Detailed Session Analysis")
        
        session = st.session_state.session
        stats = get_session_stats(session)
        
        render_session_overview(session, stats)
        st.markdown("---")
        render_analysis_tabs(session)

if __name__ == "__main__":
    main()