"""
Data loading and caching functions for F1 Analytics Dashboard
Lazy loading approach - checks data availability only when needed
"""
import streamlit as st
import fastf1
import pandas as pd
import tempfile
import warnings
from datetime import datetime, timezone

# Suppress warnings and configure cache
warnings.filterwarnings('ignore')

# Try to set up FastF1 cache
try:
    cache_dir = tempfile.mkdtemp()
    fastf1.Cache.enable_cache(cache_dir)
except Exception as e:
    st.warning(f"Cache setup warning: {e}")

# Try alternative Ergast API - fallback to default if fails
try:
    fastf1.ergast.interface.BASE_URL = "https://api.jolpi.ca/ergast/f1"
except Exception:
    # Use default Ergast API if custom one fails
    pass

@st.cache_data(ttl=3600, show_spinner=False)  # 1 hour cache for years
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
        except:
            continue
    
    # Fallback if nothing works
    if not available_years:
        available_years = [2024, 2023, 2022]
    
    return available_years

@st.cache_data(ttl=1800, show_spinner=False)  # 30 minutes cache
def get_schedule(year):
    """Get F1 schedule directly from FastF1 API, filtered to past events for current year"""
    try:
        schedule = fastf1.get_event_schedule(year)
        if schedule.empty:
            st.warning(f"No events found for {year} season")
            return []
        
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

@st.cache_data(ttl=1800, show_spinner=False)  # 30 minutes cache
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
        
        # Fastest lap details - FIXED FORMAT
        try:
            fastest_lap = session.laps.pick_fastest()
            lap_time = fastest_lap['LapTime']
            
            # Convert timedelta to proper lap time format (MM:SS.SSS)
            if pd.notna(lap_time):
                total_seconds = lap_time.total_seconds()
                minutes = int(total_seconds // 60)
                seconds = total_seconds % 60
                stats['fastest_lap_time'] = f"{minutes}:{seconds:06.3f}"
            else:
                stats['fastest_lap_time'] = 'N/A'
            
            stats['fastest_lap_driver'] = fastest_lap['Driver']
        except:
            stats['fastest_lap_time'] = 'N/A'
            stats['fastest_lap_driver'] = 'N/A'
        
        # Speed analysis
        if 'SpeedFL' in session.laps.columns:
            try:
                max_speed = session.laps['SpeedFL'].max()
                stats['max_speed'] = f"{max_speed:.1f} km/h" if pd.notna(max_speed) else "N/A"
            except:
                stats['max_speed'] = "N/A"
        
        # Average lap time - FIXED FORMAT
        try:
            valid_laps = session.laps[session.laps['LapTime'].notna()]
            if not valid_laps.empty:
                avg_total_seconds = valid_laps['LapTime'].dt.total_seconds().mean()
                avg_minutes = int(avg_total_seconds // 60)
                avg_seconds = avg_total_seconds % 60
                stats['average_lap_time'] = f"{avg_minutes}:{avg_seconds:06.3f}"
            else:
                stats['average_lap_time'] = "N/A"
        except:
            stats['average_lap_time'] = "N/A"
        
        # Session date
        try:
            if hasattr(session, 'date') and session.date:
                stats['session_date'] = session.date.strftime("%Y-%m-%d")
            else:
                stats['session_date'] = "Unknown"
        except:
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

def check_session_availability(year, event):
    """Lazy session availability check - only used when specifically needed"""
    available_sessions = []
    session_types = ['R', 'Q', 'FP3', 'FP2', 'FP1', 'S']
    
    for session_type in session_types:
        try:
            # Quick check without full load
            session = fastf1.get_session(year, event, session_type)
            
            # Try to get basic session info without loading full data
            if hasattr(session, 'session_info'):
                available_sessions.append(session_type)
            
        except Exception:
            # Skip sessions that don't exist
            continue
    
    return available_sessions

def get_race_weekend_summary(year, event):
    """Get race weekend summary with lazy approach"""
    # For lazy loading, return optimistic status
    # Actual availability will be determined when loading
    return {
        'event': event,
        'year': year,
        'available_sessions': ['R', 'Q', 'FP3', 'FP2', 'FP1'],  # Assume common sessions
        'status': 'unknown'  # Will be determined on load
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
                except:
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
                except:
                    pass
        
        return None
        
    except Exception as e:
        return None

@st.cache_data(ttl=3600, show_spinner=False)  # 1 hour cache for highlights
def get_recent_race_highlights():
    """Get highlights from recent races"""
    try:
        current_year = datetime.now().year
        highlights = []
        
        # Check recent years for highlights
        for year in [current_year, current_year-1]:
            if len(highlights) >= 3:
                break
                
            events = get_schedule(year)
            if not events:
                continue
                
            # Check recent events
            for event in reversed(events[-5:]):  # Last 5 events
                if len(highlights) >= 3:
                    break
                    
                try:
                    session = load_session(year, event, 'R')
                    if session and hasattr(session, 'laps') and not session.laps.empty:
                        fastest_lap = session.laps.pick_fastest()
                        
                        # Get podium (top 3 finishers)
                        try:
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
                            # Fallback for incomplete race data
                            highlights.append({
                                'year': year,
                                'event': event,
                                'winner': fastest_lap['Driver'],
                                'fastest_lap_driver': fastest_lap['Driver'],
                                'fastest_lap_time': str(fastest_lap['LapTime']),
                                'podium': [fastest_lap['Driver']],
                                'session_date': session.date.strftime("%Y-%m-%d") if hasattr(session, 'date') and session.date else "Unknown"
                            })
                except:
                    continue
        
        return highlights
        
    except Exception as e:
        return []

# Utility functions for testing and debugging
def test_race_loading(year, event, session_type):
    """Test function to verify race loading"""
    try:
        st.write(f"### Testing {year} {event} {session_type}")
        
        session = load_session(year, event, session_type)
        
        if session:
            stats = get_session_stats(session)
            st.success(f"✅ Loaded successfully!")
            st.write(f"**Drivers:** {stats['total_drivers']}")
            st.write(f"**Laps:** {stats['total_laps']}")
            st.write(f"**Fastest:** {stats['fastest_lap_driver']} ({stats['fastest_lap_time']})")
            return True
        else:
            st.error("❌ Failed to load")
            return False
            
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return False

def quick_session_test():
    """Quick test of multiple sessions"""
    st.write("### Quick Session Test")
    
    test_cases = [
        (2025, "Monaco Grand Prix", "R"),
        (2025, "British Grand Prix", "R"),
        (2024, "Abu Dhabi Grand Prix", "R"),
    ]
    
    for year, event, session_type in test_cases:
        with st.expander(f"{year} {event} {session_type}"):
            test_race_loading(year, event, session_type)