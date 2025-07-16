"""
Page setup and configuration
"""
import streamlit as st

def setup_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="F1 Analytics Dashboard", 
        page_icon="🏎️",
        layout="wide",
        initial_sidebar_state="expanded"
    )