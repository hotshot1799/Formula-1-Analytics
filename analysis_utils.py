"""
Analysis utility functions for F1 Analytics Dashboard
Fixed lap time formatting and position tracking
"""
import pandas as pd
import streamlit as st

def session_cache(func):
    """Cache within the current session only.

    The cache key incorporates the function name, the current session
    identity (year/event/session_type) *and* a hash of the actual
    arguments so that calls with different inputs are cached separately.
    """
    from functools import wraps
    import hashlib, pickle

    @wraps(func)
    def wrapper(*args, **kwargs):
        year = st.session_state.get('year')
        event = st.session_state.get('event')
        session_type = st.session_state.get('session_type')

        # Only cache when a session is actually loaded
        if year is None or event is None or session_type is None:
            return func(*args, **kwargs)

        # Build a deterministic hash of the call arguments
        try:
            arg_bytes = pickle.dumps((args, sorted(kwargs.items())))
            arg_hash = hashlib.md5(arg_bytes).hexdigest()
        except Exception:
            # Unhashable args → skip cache
            return func(*args, **kwargs)

        cache_key = f"{func.__name__}_{year}_{event}_{session_type}_{arg_hash}"

        if 'function_cache' not in st.session_state:
            st.session_state.function_cache = {}

        if cache_key in st.session_state.function_cache:
            return st.session_state.function_cache[cache_key]

        result = func(*args, **kwargs)
        st.session_state.function_cache[cache_key] = result
        return result

    return wrapper

def format_lap_time(lap_time):
    """Convert timedelta or seconds to MM:SS.SSS format"""
    try:
        if pd.isna(lap_time):
            return "N/A"
        
        # If it's a timedelta, convert to seconds
        if hasattr(lap_time, 'total_seconds'):
            total_seconds = lap_time.total_seconds()
        else:
            total_seconds = float(lap_time)
        
        # Handle invalid times
        if total_seconds <= 0 or total_seconds > 600:  # Over 10 minutes is invalid
            return "N/A"
        
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:06.3f}"
    except Exception:
        return "N/A"

def calculate_lap_statistics(session, selected_drivers):
    """Calculate detailed lap statistics for selected drivers with proper formatting"""
    lap_stats = []
    
    for driver in selected_drivers:
        try:
            driver_laps = session.laps[session.laps['Driver'] == driver]
            valid_laps = driver_laps[driver_laps['LapTime'].notna()]
            
            if not valid_laps.empty:
                lap_times_seconds = valid_laps['LapTime'].dt.total_seconds()
                
                lap_stats.append({
                    'Driver': driver,
                    'Best Lap': format_lap_time(lap_times_seconds.min()),
                    'Average': format_lap_time(lap_times_seconds.mean()),
                    'Worst Lap': format_lap_time(lap_times_seconds.max()),
                    'Total Laps': len(valid_laps),
                    'Consistency': f"{lap_times_seconds.std():.3f}s"
                })
        except Exception as e:
            # Add driver with N/A values if there's an error
            lap_stats.append({
                'Driver': driver,
                'Best Lap': 'N/A',
                'Average': 'N/A', 
                'Worst Lap': 'N/A',
                'Total Laps': 0,
                'Consistency': 'N/A'
            })
    
    return pd.DataFrame(lap_stats) if lap_stats else None

def get_fastest_sector_times(df):
    """Get fastest times for each sector"""
    if df is None or df.empty:
        return None, None, None
    
    try:
        fastest_s1 = df.loc[df['Sector1'].idxmin()]
        fastest_s2 = df.loc[df['Sector2'].idxmin()]
        fastest_s3 = df.loc[df['Sector3'].idxmin()]
        
        return fastest_s1, fastest_s2, fastest_s3
    except Exception:
        return None, None, None

def get_telemetry_insights(session, driver1, driver2):
    """Get telemetry insights for two drivers"""
    try:
        lap1 = session.laps.pick_driver(driver1).pick_fastest()
        lap2 = session.laps.pick_driver(driver2).pick_fastest()
        tel1 = lap1.get_telemetry()
        tel2 = lap2.get_telemetry()
        
        insights = {
            driver1: {
                'max_speed': tel1['Speed'].max(),
                'avg_speed': tel1['Speed'].mean(),
                'avg_throttle': tel1['Throttle'].mean() if 'Throttle' in tel1.columns else None
            },
            driver2: {
                'max_speed': tel2['Speed'].max(),
                'avg_speed': tel2['Speed'].mean(),
                'avg_throttle': tel2['Throttle'].mean() if 'Throttle' in tel2.columns else None
            }
        }
        
        return insights
        
    except Exception:
        return None

def prepare_export_data(session):
    """Prepare data for export with proper lap time formatting"""
    try:
        # Select columns to display
        available_cols = ['Driver', 'LapNumber', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 
                         'Position', 'SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST']
        display_cols = [col for col in available_cols if col in session.laps.columns]
        
        lap_data = session.laps[display_cols].copy()
        
        # Convert timedelta columns to proper format
        time_cols = ['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']
        for col in time_cols:
            if col in lap_data.columns:
                lap_data[col] = lap_data[col].apply(format_lap_time)
        
        return lap_data
    except Exception as e:
        st.error(f"Error preparing export data: {e}")
        return None

def format_session_info(stats):
    """Format session information for display"""
    info_text = ""
    
    try:
        if stats.get('track_name') and stats.get('max_speed'):
            info_text = f"**📍 {stats.get('track_name')}** | **⚡ Max Speed: {stats.get('max_speed')}**"
        elif stats.get('track_name'):
            info_text = f"**📍 {stats.get('track_name')}**"
    except Exception:
        pass
    
    return info_text

def get_season_indicator(year):
    """Get season indicator text and style"""
    current_year = 2025
    
    if year == current_year:
        return f"🏁 {year} season - Live ongoing season!", "success"
    elif year == 2024:
        return "🏆 Complete 2024 season data", "success"
    elif year == 2023:
        return "📚 2023 historical data", "info"
    else:
        return f"📚 {year} historical data", "info"

def get_position_data_safe(session):
    """Safely extract position data from session with proper driver identification.

    Uses vectorized pandas operations instead of row-by-row iteration.
    """
    try:
        if not hasattr(session, 'laps') or session.laps.empty:
            return None

        if 'Position' not in session.laps.columns:
            return None

        # Determine the best driver identifier column
        has_driver = 'Driver' in session.laps.columns
        has_driver_number = 'DriverNumber' in session.laps.columns

        if has_driver:
            cols = ['LapNumber', 'Driver', 'Position']
        elif has_driver_number:
            cols = ['LapNumber', 'DriverNumber', 'Position']
        else:
            return None

        position_df = session.laps[cols].dropna(subset=['Position']).copy()

        if position_df.empty:
            return None

        position_df['Position'] = position_df['Position'].astype(int)
        position_df['LapNumber'] = position_df['LapNumber'].astype(int)

        # If we only have DriverNumber, map to abbreviation
        if not has_driver and has_driver_number:
            driver_mapping = {}
            if hasattr(session, 'results') and not session.results.empty:
                valid = session.results.dropna(subset=['DriverNumber', 'Abbreviation'])
                driver_mapping = dict(zip(
                    valid['DriverNumber'].astype(int).astype(str),
                    valid['Abbreviation'],
                ))
            position_df['Driver'] = (
                position_df['DriverNumber']
                .astype(int).astype(str)
                .map(driver_mapping)
                .fillna(position_df['DriverNumber'].astype(str))
            )
            position_df = position_df.drop(columns=['DriverNumber'])

        # Drop any rows where Driver ended up NaN
        position_df = position_df.dropna(subset=['Driver'])

        if position_df.empty:
            return None

        return position_df[['LapNumber', 'Driver', 'Position']].reset_index(drop=True)

    except Exception as e:
        return None

@session_cache
def calculate_position_changes(position_df, session=None):
    """Calculate position changes throughout the race using starting grid positions.

    Parameters
    ----------
    position_df : pd.DataFrame
        DataFrame with columns LapNumber, Driver, Position.
    session : fastf1 Session, optional
        The session object.  If *None*, falls back to
        ``st.session_state.session`` for backwards compatibility.

    Returns
    -------
    dict
        ``{"data": pd.DataFrame | None, "warnings": list[str]}``
        The caller is responsible for displaying any warnings.
    """
    warnings_list = []

    try:
        if position_df is None or position_df.empty:
            return {"data": None, "warnings": warnings_list}

        if session is None:
            session = st.session_state.get('session')
        if session is None:
            return {"data": None, "warnings": ["No session available"]}

        # Build driver name mappings from results
        driver_name_mapping = {}
        driver_full_name_mapping = {}

        if hasattr(session, 'results') and not session.results.empty:
            try:
                for _, row in session.results.iterrows():
                    if pd.notna(row.get('DriverNumber')) and pd.notna(row.get('Abbreviation')):
                        driver_num = str(int(row['DriverNumber']))
                        driver_name_mapping[driver_num] = row['Abbreviation']

                    if pd.notna(row.get('Abbreviation')):
                        driver_code = row['Abbreviation']
                        driver_name_mapping[driver_code] = driver_code
                        if pd.notna(row.get('FullName')):
                            driver_full_name_mapping[driver_code] = row['FullName']
            except Exception:
                pass

        # Determine start & final positions
        start_positions = None
        final_positions = None

        if hasattr(session, 'results') and not session.results.empty:
            try:
                results = session.results
                grid_positions = {}
                finish_positions = {}

                for _, row in results.iterrows():
                    if pd.notna(row.get('Abbreviation')):
                        driver_code = row['Abbreviation']

                        if pd.notna(row.get('GridPosition')):
                            try:
                                grid_positions[driver_code] = int(row['GridPosition'])
                            except Exception:
                                pass

                        if pd.notna(row.get('Position')):
                            try:
                                finish_positions[driver_code] = int(row['Position'])
                            except Exception:
                                pass

                if grid_positions:
                    start_positions = pd.Series(grid_positions)
                    warnings_list.append("Using starting grid positions from race results")

                if finish_positions:
                    final_positions = pd.Series(finish_positions)
                else:
                    final_positions = position_df.groupby('Driver')['Position'].last().dropna().astype(int)

            except Exception as e:
                warnings_list.append(f"Could not extract grid positions from results: {e}")

        if start_positions is None:
            warnings_list.append("No starting grid data available - using first lap positions as fallback")
            start_positions = position_df.groupby('Driver')['Position'].first().dropna().astype(int)

        if final_positions is None:
            final_positions = position_df.groupby('Driver')['Position'].last().dropna().astype(int)

        # Calculate position changes
        common_drivers = set(start_positions.index) & set(final_positions.index)
        changes = []

        for driver in common_drivers:
            start_pos = start_positions.get(driver)
            final_pos = final_positions.get(driver)

            if start_pos is not None and final_pos is not None:
                driver_code = driver_name_mapping.get(driver, driver)
                full_name = driver_full_name_mapping.get(driver_code, driver_code)

                changes.append({
                    'Driver': driver_code,
                    'Full Name': full_name,
                    'Start Position': start_pos,
                    'Final Position': final_pos,
                    'Positions Gained': start_pos - final_pos,
                })

        if not changes:
            return {"data": None, "warnings": warnings_list}

        changes_df = pd.DataFrame(changes).sort_values('Positions Gained', ascending=False)
        return {"data": changes_df, "warnings": warnings_list}

    except Exception as e:
        warnings_list.append(f"Error calculating position changes: {e}")
        return {"data": None, "warnings": warnings_list}