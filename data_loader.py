"""
Data loading and caching functions for F1 Analytics Dashboard
"""
import streamlit as st
import fastf1
import pandas as pd
import tempfile
import warnings
from datetime import datetime, timedelta

# Suppress warnings and configure cache
warnings.filterwarnings('ignore')
fastf1.Cache.enable_cache(tempfile.mkdtemp())

@st.cache_data(ttl=3600, show_spinner=False)  # 1 hour cache for current season
def get_available_years():
    """Get available F1 years with data"""
    current_year = datetime.now().year
    available_years = []
    
    # Always include current year and recent years
    years_to_check = [current_year, current_year-1, current_year-2]
    
    for year in years_to_check:
        try:
            schedule = fastf1.get_event_schedule(year)
            if not schedule.empty:
                available_years.append(year)
        except:
            continue
    
    return sorted(available_years, reverse=True)

@st.cache_data(ttl=3600, show_spinner=False)
def get_schedule(year):
    """Get F1 schedule for a given year"""
    try:
        schedule = fastf1.get_event_schedule(year)
        if schedule.empty:
            st.warning(f"No events found for {year} season")
            return []
        
        events = schedule['EventName'].tolist()
        
        # For current year, filter to show completed and current weekend events
        if year == datetime.now().year:
            current_date = datetime.now()
            completed_events = []
            
            for event_name in events:
                try:
                    # Try to load a session to check if data exists
                    # Start with Race, then Qualifying, then Practice
                    for session_type in ['R', 'Q', 'FP3', 'FP2', 'FP1']:
                        try:
                            session = fastf1.get_session(year, event_name, session_type)
                            # Check if session has occurred and has data
                            if hasattr(session, 'date') and session.date:
                                # Add events from the past 2 weeks to account for data processing delays
                                cutoff_date = current_date - timedelta(days=14)
                                if session.date <= current_date.date():
                                    completed_events.append(event_name)
                                    break
                            else:
                                # If no date info, try to load session data
                                session.load()
                                if hasattr(session, 'laps') and not session.laps.empty:
                                    completed_events.append(event_name)
                                    break
                        except:
                            continue
                except:
                    continue
            
            if completed_events:
                # Remove duplicates while preserving order
                seen = set()
                unique_events = []
                for event in completed_events:
                    if event not in seen:
                        seen.add(event)
                        unique_events.append(event)
                return unique_events
            else:
                # Fallback: return first few events if detection fails
                return events[:10]
        
        return events
        
    except Exception as e:
        st.error(f"Error loading schedule for {year}: {e}")
        return []

@st.cache_data(ttl=1800, show_spinner=False)
def load_session(year, event, session_type):
    """Load F1 session data"""
    try:
        session = fastf1.get_session(year, event, session_type)
        
        # Check if session exists
        if session is None:
            return None
            
        session.load()
        
        # Verify session has lap data
        if hasattr(session, 'laps') and not session.laps.empty:
            return session
        else:
            return None
            
    except Exception as e:
        # Don't show error for expected failures (future sessions)
        if "not yet available" in str(e).lower() or "no data" in str(e).lower():
            return None
        st.error(f"Error loading {event} {session_type}: {str(e)[:100]}")
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
        
        # Session date
        try:
            if hasattr(session, 'date') and session.date:
                stats['session_date'] = session.date.strftime("%Y-%m-%d")
        except:
            pass
        
        return stats
        
    except Exception as e:
        st.error(f"Error calculating stats: {e}")
        return {}

def check_session_availability(year, event):
    """Check which sessions are available for a given event"""
    available_sessions = []
    session_types = ['R', 'Q', 'FP3', 'FP2', 'FP1', 'S']  # Include Sprint
    
    for session_type in session_types:
        try:
            session = fastf1.get_session(year, event, session_type)
            session.load()
            if hasattr(session, 'laps') and not session.laps.empty:
                available_sessions.append(session_type)
        except:
            continue
    
    return available_sessions

def get_latest_race_data():
    """Get the most recent race data available"""
    try:
        current_year = datetime.now().year
        
        # Get available years
        available_years = []
        for year in range(current_year, 2017, -1):
            try:
                schedule = fastf1.get_event_schedule(year)
                if not schedule.empty:
                    available_years.append(year)
            except:
                continue
        
        # Find the most recent race
        for year in available_years:
            events = get_schedule(year)
            if not events:
                continue
                
            # Check events in reverse order (most recent first)
            for event in reversed(events):
                # Try to load race session first
                try:
                    session = fastf1.get_session(year, event, 'R')
                    session.load()
                    if hasattr(session, 'laps') and not session.laps.empty:
                        return {
                            'year': year,
                            'event': event,
                            'session_type': 'R',
                            'session': session,
                            'status': 'race_complete'
                        }
                except:
                    pass
                
                # If no race, try qualifying
                try:
                    session = fastf1.get_session(year, event, 'Q')
                    session.load()
                    if hasattr(session, 'laps') and not session.laps.empty:
                        return {
                            'year': year,
                            'event': event,
                            'session_type': 'Q',
                            'session': session,
                            'status': 'qualifying_complete'
                        }
                except:
                    pass
        
        return None
        
    except Exception as e:
        return None

@st.cache_data(ttl=1800, show_spinner=False)
def get_recent_race_highlights():
    """Get highlights from recent races"""
    try:
        current_year = datetime.now().year
        highlights = []
        
        # Get last 3 completed races
        for year in [current_year, current_year-1]:
            events = get_schedule(year)
            if not events:
                continue
                
            for event in reversed(events):
                if len(highlights) >= 3:
                    break
                    
                try:
                    session = fastf1.get_session(year, event, 'R')
                    session.load()
                    if hasattr(session, 'laps') and not session.laps.empty:
                        fastest_lap = session.laps.pick_fastest()
                        
                        # Get podium (top 3 finishers)
                        final_positions = session.laps.groupby('Driver')['Position'].last().dropna()
                        podium = final_positions.sort_values().head(3)
                        
                        highlights.append({
                            'year': year,
                            'event': event,
                            'winner': podium.index[0] if len(podium) > 0 else "Unknown",
                            'fastest_lap_driver': fastest_lap['Driver'],
                            'fastest_lap_time': str(fastest_lap['LapTime']),
                            'podium': list(podium.index[:3]),
                            'session_date': session.date.strftime("%Y-%m-%d") if hasattr(session, 'date') and session.date else "Unknown"
                        })
                except:
                    continue
        
        return highlights
        
    except Exception as e:
        return []
    """Get summary of available data for a race weekend"""
    try:
        summary = {
            'event': event,
            'year': year,
            'available_sessions': check_session_availability(year, event),
            'status': 'unknown'
        }
        
        # Determine weekend status
        if 'R' in summary['available_sessions']:
            summary['status'] = 'completed'
        elif 'Q' in summary['available_sessions']:
            summary['status'] = 'qualifying_done'
        elif any(fp in summary['available_sessions'] for fp in ['FP1', 'FP2', 'FP3']):
            summary['status'] = 'practice_only'
        else:
            summary['status'] = 'no_data'
        
        return summary
        
    except Exception as e:
        return {'event': event, 'year': year, 'available_sessions': [], 'status': 'error'}