"""
Data loading and caching functions for F1 Analytics Dashboard
Optimized for 2025 ongoing season with enhanced error handling
"""
import streamlit as st
import fastf1
import pandas as pd
import tempfile
import warnings
from datetime import datetime, timedelta

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

# 2025 F1 Season Data - Updated as of July 15, 2025
F1_2025_COMPLETED_RACES = [
    "British Grand Prix",        # July 4-6 (most recent)
    "Austrian Grand Prix",       # June 27-29
    "Canadian Grand Prix",       # June 13-15
    "Spanish Grand Prix",        # May 30-Jun 1
    "Monaco Grand Prix",         # May 23-25
    "Emilia Romagna Grand Prix", # May 16-18
    "Miami Grand Prix",          # May 2-4
    "Saudi Arabian Grand Prix",  # April 18-20
    "Bahrain Grand Prix",        # April 11-13
    "Japanese Grand Prix",       # April 4-6
    "Chinese Grand Prix",        # March 21-23
    "Australian Grand Prix"      # March 14-16 (season opener)
]

F1_2025_UPCOMING_RACES = [
    "Belgian Grand Prix",        # July 25-27 (next race)
    "Hungarian Grand Prix",      # August 1-3
    "Dutch Grand Prix",          # August 29-31
]

@st.cache_data(ttl=3600, show_spinner=False)  # 1 hour cache for years
def get_available_years():
    """Get available F1 years with data - prioritize 2025"""
    current_year = datetime.now().year
    available_years = []
    
    # Always include 2025 first (ongoing season)
    available_years.append(2025)
    
    # Add recent years
    years_to_check = [2024, 2023, 2022]
    
    for year in years_to_check:
        try:
            schedule = fastf1.get_event_schedule(year)
            if not schedule.empty:
                available_years.append(year)
        except:
            continue
    
    return available_years

@st.cache_data(ttl=1800, show_spinner=False)  # 30 minutes cache for 2025 (live season)
def get_schedule(year):
    """Get F1 schedule for a given year - optimized for 2025"""
    try:
        # Special handling for 2025 ongoing season
        if year == 2025:
            return get_2025_schedule_optimized()
        
        # For historical years
        schedule = fastf1.get_event_schedule(year)
        if schedule.empty:
            st.warning(f"No events found for {year} season")
            return []
        
        events = schedule['EventName'].tolist()
        
        # For current year (if not 2025), filter completed events
        if year == datetime.now().year and year != 2025:
            current_date = datetime.now()
            completed_events = []
            
            for event_name in events:
                try:
                    for session_type in ['R', 'Q', 'FP3', 'FP2', 'FP1']:
                        try:
                            session = fastf1.get_session(year, event_name, session_type)
                            if hasattr(session, 'date') and session.date:
                                cutoff_date = current_date - timedelta(days=14)
                                if session.date <= current_date.date():
                                    completed_events.append(event_name)
                                    break
                        except:
                            continue
                except:
                    continue
            
            if completed_events:
                seen = set()
                unique_events = []
                for event in completed_events:
                    if event not in seen:
                        seen.add(event)
                        unique_events.append(event)
                return unique_events
        
        return events
        
    except Exception as e:
        st.error(f"Error loading schedule for {year}: {e}")
        return []

def get_2025_schedule_optimized():
    """Get optimized 2025 schedule focusing on completed races"""
    try:
        # Try to get full schedule first
        schedule = fastf1.get_event_schedule(2025)
        if not schedule.empty:
            all_events = schedule['EventName'].tolist()
            
            # Filter to completed + next upcoming race
            completed_and_next = F1_2025_COMPLETED_RACES.copy()
            completed_and_next.extend(F1_2025_UPCOMING_RACES[:1])  # Add next race
            
            # Keep only events that exist in the official schedule
            filtered_events = [event for event in completed_and_next if event in all_events]
            
            if filtered_events:
                return filtered_events
        
        # Fallback to our known list
        return F1_2025_COMPLETED_RACES
        
    except Exception as e:
        st.warning(f"Using fallback 2025 schedule: {e}")
        return F1_2025_COMPLETED_RACES

@st.cache_data(ttl=1800, show_spinner=False)  # 30 minutes for 2025, 1 hour for others
def load_session(year, event, session_type):
    """Load F1 session data with enhanced 2025 support"""
    try:
        # Special handling for 2025 live season
        if year == 2025:
            return load_2025_session_optimized(event, session_type)
        
        # Standard loading for historical years
        session = fastf1.get_session(year, event, session_type)
        
        if session is None:
            return None
            
        session.load()
        
        # Verify session has lap data
        if hasattr(session, 'laps') and not session.laps.empty:
            return session
        else:
            return None
            
    except Exception as e:
        error_msg = str(e).lower()
        if "not yet available" in error_msg or "no data" in error_msg:
            return None
        elif "connection" in error_msg or "timeout" in error_msg:
            st.error(f"🌐 Network error loading {event} {session_type}. F1 servers may be busy - try again in a few minutes.")
        else:
            st.error(f"Error loading {event} {session_type}: {str(e)[:100]}")
        return None

def load_2025_session_optimized(event, session_type):
    """Optimized session loading specifically for 2025 season"""
    try:
        # Show 2025-specific loading message
        with st.spinner(f"Loading 2025 {event} {session_type} data..."):
            session = fastf1.get_session(2025, event, session_type)
            
            if session is None:
                return None
            
            # Load with progress indication
            session.load()
            
            # Verify data quality for 2025
            if hasattr(session, 'laps') and not session.laps.empty:
                lap_count = len(session.laps)
                
                # Quality checks for 2025 data
                if lap_count > 50:  # Full session
                    return session
                elif lap_count > 10:  # Partial but usable data
                    st.info(f"ℹ️ {event} {session_type}: Limited data available ({lap_count} laps)")
                    return session
                elif lap_count > 0:  # Minimal data
                    st.warning(f"⚠️ {event} {session_type}: Very limited data ({lap_count} laps)")
                    return session
                else:
                    return None
            else:
                return None
                
    except Exception as e:
        error_msg = str(e).lower()
        
        # 2025-specific error handling
        if "not yet available" in error_msg:
            if event in F1_2025_UPCOMING_RACES:
                st.info(f"🏁 {event} {session_type} is scheduled but hasn't occurred yet")
            else:
                st.info(f"📊 {event} {session_type} data is still being processed (try again in 1-2 hours)")
        elif "no data" in error_msg:
            st.warning(f"📋 No data available for {event} {session_type} - try a different session type")
        elif "connection" in error_msg or "timeout" in error_msg:
            st.error(f"🌐 Network error loading {event} {session_type}. F1 servers may be busy after recent races.")
        elif "403" in error_msg or "forbidden" in error_msg:
            st.error(f"🔒 Access restricted for {event} {session_type}. Data may not be released yet.")
        else:
            st.error(f"❌ Error loading {event} {session_type}: {str(e)[:100]}")
        
        return None

def get_session_stats(session):
    """Get detailed session statistics with enhanced 2025 features"""
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
            stats['fastest_lap_time'] = str(fastest_lap['LapTime'])
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
        
        # Average lap time
        try:
            valid_laps = session.laps[session.laps['LapTime'].notna()]
            if not valid_laps.empty:
                avg_seconds = valid_laps['LapTime'].dt.total_seconds().mean()
                stats['average_lap_time'] = f"{avg_seconds:.3f}s"
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
            'fastest_lap_driver': 'N/A'
        }

def check_session_availability(year, event):
    """Check which sessions are available for a given event - optimized for 2025"""
    available_sessions = []
    
    # For 2025, use optimized checking
    if year == 2025:
        return check_2025_session_availability(event)
    
    # For historical years, use standard checking
    session_types = ['R', 'Q', 'FP3', 'FP2', 'FP1', 'S']
    
    for session_type in session_types:
        try:
            session = fastf1.get_session(year, event, session_type)
            session.load()
            if hasattr(session, 'laps') and not session.laps.empty:
                available_sessions.append(session_type)
        except:
            continue
    
    return available_sessions

def check_2025_session_availability(event):
    """Optimized session availability check for 2025"""
    available_sessions = []
    session_types = ['R', 'Q', 'S', 'FP3', 'FP2', 'FP1']  # Prioritize main sessions
    
    # Quick check for upcoming races
    if event in F1_2025_UPCOMING_RACES:
        return []  # No sessions available yet
    
    # For completed races, check efficiently
    for session_type in session_types:
        try:
            session = fastf1.get_session(2025, event, session_type)
            
            # Quick date check first
            if hasattr(session, 'date') and session.date:
                current_date = datetime.now().date()
                if session.date <= current_date:
                    # Only do full load for very recent sessions
                    if (current_date - session.date).days <= 3:
                        session.load()
                        if hasattr(session, 'laps') and not session.laps.empty:
                            available_sessions.append(session_type)
                    else:
                        # Assume older sessions have data
                        available_sessions.append(session_type)
            
        except:
            continue
    
    return available_sessions

def get_race_weekend_summary(year, event):
    """Get summary of available data for a race weekend"""
    try:
        available_sessions = check_session_availability(year, event)
        
        summary = {
            'event': event,
            'year': year,
            'available_sessions': available_sessions,
            'status': 'unknown'
        }
        
        # Determine weekend status
        if 'R' in available_sessions:
            summary['status'] = 'completed'
        elif 'Q' in available_sessions:
            summary['status'] = 'qualifying_done'
        elif any(fp in available_sessions for fp in ['FP1', 'FP2', 'FP3']):
            summary['status'] = 'practice_only'
        else:
            if year == 2025 and event in F1_2025_UPCOMING_RACES:
                summary['status'] = 'upcoming'
            else:
                summary['status'] = 'no_data'
        
        return summary
        
    except Exception as e:
        return {'event': event, 'year': year, 'available_sessions': [], 'status': 'error'}

def get_latest_race_data():
    """Get the most recent race data available - prioritize 2025"""
    try:
        # First, try to get latest 2025 race
        latest_2025 = get_latest_2025_race()
        if latest_2025:
            return latest_2025
        
        # Fallback to historical data
        return get_latest_historical_race()
        
    except Exception as e:
        st.warning(f"Error getting latest race data: {e}")
        return None

def get_latest_2025_race():
    """Get the most recent 2025 race with data"""
    try:
        # Check completed 2025 races in reverse order (most recent first)
        for event in F1_2025_COMPLETED_RACES:
            # Try race session first
            try:
                session = load_2025_session_optimized(event, 'R')
                if session and hasattr(session, 'laps') and not session.laps.empty:
                    return {
                        'year': 2025,
                        'event': event,
                        'session_type': 'R',
                        'session': session,
                        'status': 'race_complete'
                    }
            except:
                pass
            
            # Try qualifying if no race data
            try:
                session = load_2025_session_optimized(event, 'Q')
                if session and hasattr(session, 'laps') and not session.laps.empty:
                    return {
                        'year': 2025,
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

def get_latest_historical_race():
    """Get latest race from historical years as fallback"""
    try:
        for year in [2024, 2023]:
            events = get_schedule(year)
            if not events:
                continue
                
            for event in reversed(events):
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
                    continue
        
        return None
        
    except Exception as e:
        return None

@st.cache_data(ttl=3600, show_spinner=False)  # 1 hour cache for highlights
def get_recent_race_highlights():
    """Get highlights from recent races - prioritize 2025"""
    try:
        highlights = []
        
        # Get 2025 highlights first
        recent_2025_races = F1_2025_COMPLETED_RACES[:5]  # Latest 5 races
        
        for event in recent_2025_races:
            if len(highlights) >= 3:
                break
                
            try:
                session = fastf1.get_session(2025, event, 'R')
                session.load()
                if hasattr(session, 'laps') and not session.laps.empty:
                    fastest_lap = session.laps.pick_fastest()
                    
                    # Get podium (top 3 finishers)
                    try:
                        final_positions = session.laps.groupby('Driver')['Position'].last().dropna()
                        podium = final_positions.sort_values().head(3)
                        
                        highlights.append({
                            'year': 2025,
                            'event': event,
                            'winner': podium.index[0] if len(podium) > 0 else "Unknown",
                            'fastest_lap_driver': fastest_lap['Driver'],
                            'fastest_lap_time': str(fastest_lap['LapTime']),
                            'podium': list(podium.index[:3]),
                            'session_date': session.date.strftime("%Y-%m-%d") if hasattr(session, 'date') and session.date else "Unknown"
                        })
                    except:
                        # Fallback for qualifying or incomplete race data
                        highlights.append({
                            'year': 2025,
                            'event': event,
                            'winner': fastest_lap['Driver'],
                            'fastest_lap_driver': fastest_lap['Driver'],
                            'fastest_lap_time': str(fastest_lap['LapTime']),
                            'podium': [fastest_lap['Driver']],
                            'session_date': session.date.strftime("%Y-%m-%d") if hasattr(session, 'date') and session.date else "Unknown"
                        })
            except:
                continue
        
        # Fill remaining slots with 2024 data if needed
        if len(highlights) < 3:
            try:
                events_2024 = get_schedule(2024)
                for event in reversed(events_2024[-5:]):  # Last 5 races of 2024
                    if len(highlights) >= 3:
                        break
                    
                    try:
                        session = fastf1.get_session(2024, event, 'R')
                        session.load()
                        if hasattr(session, 'laps') and not session.laps.empty:
                            fastest_lap = session.laps.pick_fastest()
                            final_positions = session.laps.groupby('Driver')['Position'].last().dropna()
                            podium = final_positions.sort_values().head(3)
                            
                            highlights.append({
                                'year': 2024,
                                'event': event,
                                'winner': podium.index[0] if len(podium) > 0 else "Unknown",
                                'fastest_lap_driver': fastest_lap['Driver'],
                                'fastest_lap_time': str(fastest_lap['LapTime']),
                                'podium': list(podium.index[:3]),
                                'session_date': session.date.strftime("%Y-%m-%d") if hasattr(session, 'date') and session.date else "Unknown"
                            })
                    except:
                        continue
            except:
                pass
        
        return highlights
        
    except Exception as e:
        return []

# Utility function to test 2025 data access
def test_2025_data_access():
    """Test function to verify 2025 data access - for debugging"""
    try:
        st.write("### 🧪 Testing 2025 F1 Data Access")
        
        # Test latest race
        latest_race = "British Grand Prix"
        session = fastf1.get_session(2025, latest_race, 'R')
        session.load()
        
        if hasattr(session, 'laps') and not session.laps.empty:
            st.success(f"✅ {latest_race}: {len(session.laps)} laps available")
            return True
        else:
            st.error(f"❌ {latest_race}: No lap data")
            return False
            
    except Exception as e:
        st.error(f"❌ Test failed: {e}")
        return False