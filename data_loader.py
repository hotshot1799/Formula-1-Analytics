"""
Data loading and caching functions for F1 Analytics Dashboard
Lazy loading approach - checks data availability only when needed
"""
import streamlit as st
import fastf1
import pandas as pd
import logging
import warnings
from datetime import datetime, timezone

import cache_config  # noqa: F401  — initializes FastF1 cache & Ergast URL
from analysis_utils import format_lap_time

# Suppress warnings
warnings.filterwarnings('ignore')

@st.cache_data(ttl=7200, max_entries=3, show_spinner=False)
def get_available_years():
    """Get available F1 years with data"""
    current_year = datetime.now().year
    available_years = []
    
    # Check recent years
    years_to_check = [current_year, current_year-1, current_year-2, current_year-3]
    
    for year in years_to_check:
        try:
            schedule = fastf1.get_event_schedule(year)
            if not schedule.empty:
                available_years.append(year)
        except Exception:
            continue
    
    # Fallback if nothing works
    if not available_years:
        available_years = [2024, 2023, 2022]
    
    return available_years

@st.cache_data(ttl=3600, max_entries=5, show_spinner=False)
def get_schedule(year):
    """Get F1 schedule directly from FastF1 API, filtered to past events for current year"""
    try:
        schedule = fastf1.get_event_schedule(year)
        if schedule.empty:
            st.warning(f"No events found for {year} season")
            return []
        
        # Ensure Session5DateUtc is datetime with UTC
        schedule['Session5DateUtc'] = pd.to_datetime(schedule['Session5DateUtc'], utc=True)
        
        events = schedule['EventName'].tolist()
        
        # For current year, filter to past events only (race date <= now)
        if year == datetime.now().year:
            now_utc = datetime.now(timezone.utc)
            past_schedule = schedule[schedule['Session5DateUtc'] <= now_utc]  # Session5 is the race
            events = past_schedule.sort_values('Session5DateUtc', ascending=False)['EventName'].tolist()  # Most recent first
        
        # For past years, return all (assumed complete)
        return events
        
    except Exception as e:
        st.error(f"Error loading schedule for {year}: {e}")
        return []

@st.cache_data(ttl=1800, max_entries=20, show_spinner=False)
def load_session(year, event, session_type):
    """Load F1 session data with lazy loading approach"""
    try:
        # Direct session loading without pre-checking
        session = fastf1.get_session(year, event, session_type)
        
        if session is None:
            return None
            
        # Load the session data
        session.load()
        
        # Verify session has meaningful data
        if hasattr(session, 'laps') and not session.laps.empty:
            return session
        else:
            return None
            
    except Exception as e:
        error_msg = str(e).lower()
        
        # Provide helpful error messages based on error type
        if "not yet available" in error_msg:
            st.info(f"🏁 {event} {session_type} hasn't occurred yet or data is still being processed")
        elif "no data" in error_msg:
            st.warning(f"📊 No data available for {event} {session_type}")
        elif "connection" in error_msg or "timeout" in error_msg:
            st.error(f"🌐 Network error loading {event} {session_type}. Please try again.")
        elif "403" in error_msg or "forbidden" in error_msg:
            st.error(f"🔒 Access restricted for {event} {session_type}. Data may not be released yet.")
        else:
            st.error(f"❌ Error loading {event} {session_type}: {str(e)[:100]}")
        
        return None

def get_session_stats(session):
    """Get detailed session statistics with proper lap time formatting"""
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
        try:
            fastest_lap = session.laps.pick_fastest()
            stats['fastest_lap_time'] = format_lap_time(fastest_lap['LapTime'])
            stats['fastest_lap_driver'] = fastest_lap['Driver']
        except Exception:
            stats['fastest_lap_time'] = 'N/A'
            stats['fastest_lap_driver'] = 'N/A'
        
        # Speed analysis
        if 'SpeedFL' in session.laps.columns:
            try:
                max_speed = session.laps['SpeedFL'].max()
                stats['max_speed'] = f"{max_speed:.1f} km/h" if pd.notna(max_speed) else "N/A"
            except Exception:
                stats['max_speed'] = "N/A"
        
        # Average lap time
        try:
            valid_laps = session.laps[session.laps['LapTime'].notna()]
            if not valid_laps.empty:
                avg_total_seconds = valid_laps['LapTime'].dt.total_seconds().mean()
                stats['average_lap_time'] = format_lap_time(avg_total_seconds)
            else:
                stats['average_lap_time'] = "N/A"
        except Exception:
            stats['average_lap_time'] = "N/A"
        
        # Session date
        try:
            if hasattr(session, 'date') and session.date:
                stats['session_date'] = session.date.strftime("%Y-%m-%d")
            else:
                stats['session_date'] = "Unknown"
        except Exception:
            stats['session_date'] = "Unknown"
        
        return stats
        
    except Exception as e:
        st.error(f"Error calculating stats: {e}")
        return {
            'total_laps': 0,
            'total_drivers': 0,
            'session_type': 'Unknown',
            'track_name': 'Unknown',
            'fastest_lap_time': 'N/A',
            'fastest_lap_driver': 'N/A',
            'session_date': 'Unknown'
        }

def get_latest_race_data():
    """Get the most recent race data available"""
    try:
        current_year = datetime.now().year
        
        # Check recent years
        for year in [current_year, current_year-1]:
            events = get_schedule(year)
            if not events:
                continue
            
            # For ongoing season, events are already filtered and sorted recent-first
            for event in events:
                # Try race session first
                try:
                    session = load_session(year, event, 'R')
                    if session and hasattr(session, 'laps') and not session.laps.empty:
                        return {
                            'year': year,
                            'event': event,
                            'session_type': 'R',
                            'session': session,
                            'status': 'race_complete'
                        }
                except Exception:
                    pass
                
                # Try qualifying if no race data
                try:
                    session = load_session(year, event, 'Q')
                    if session and hasattr(session, 'laps') and not session.laps.empty:
                        return {
                            'year': year,
                            'event': event,
                            'session_type': 'Q',
                            'session': session,
                            'status': 'qualifying_complete'
                        }
                except Exception:
                    pass
        
        return None
        
    except Exception as e:
        return None

