"""
Data loading and caching functions for F1 Analytics Dashboard
"""
import streamlit as st
import fastf1
import pandas as pd
import tempfile
import warnings

# Suppress warnings and configure cache
warnings.filterwarnings('ignore')
fastf1.Cache.enable_cache(tempfile.mkdtemp())

@st.cache_data(ttl=1800, show_spinner=False)
def get_schedule(year):
    """Get F1 schedule for a given year"""
    try:
        return fastf1.get_event_schedule(year)['EventName'].tolist()
    except Exception as e:
        st.error(f"Error loading schedule: {e}")
        return []

@st.cache_data(ttl=1800, show_spinner=False)
def load_session(year, event, session_type):
    """Load F1 session data"""
    try:
        session = fastf1.get_session(year, event, session_type)
        session.load()
        return session
    except Exception as e:
        st.error(f"Error loading session: {e}")
        return None

def get_session_stats(session):
    """Get detailed session statistics"""
    try:
        stats = {}
        
        # Basic info
        stats['total_laps'] = len(session.laps)
        stats['total_drivers'] = len(session.laps['Driver'].unique())
        
        # Session info
        session_info = session.session_info
        stats['session_type'] = session_info.get('Type', 'Unknown')
        stats['track_name'] = session_info.get('Location', 'Unknown')
        stats['event_name'] = session_info.get('EventName', 'Unknown')
        
        # Fastest lap details
        fastest_lap = session.laps.pick_fastest()
        stats['fastest_lap_time'] = str(fastest_lap['LapTime'])
        stats['fastest_lap_driver'] = fastest_lap['Driver']
        
        # Speed analysis
        if 'SpeedFL' in session.laps.columns:
            max_speed = session.laps['SpeedFL'].max()
            stats['max_speed'] = f"{max_speed:.1f} km/h" if pd.notna(max_speed) else "N/A"
        
        # Average lap time
        valid_laps = session.laps[session.laps['LapTime'].notna()]
        if not valid_laps.empty:
            avg_seconds = valid_laps['LapTime'].dt.total_seconds().mean()
            stats['average_lap_time'] = f"{avg_seconds:.3f}s"
        
        return stats
        
    except Exception as e:
        st.error(f"Error calculating stats: {e}")
        return {}