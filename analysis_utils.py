"""
Analysis utility functions for F1 Analytics Dashboard
Fixed lap time formatting and position tracking
"""
import pandas as pd
import streamlit as st

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
    except:
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
    except:
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
    except:
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
    """Safely extract position data from session"""
    try:
        if not hasattr(session, 'laps') or session.laps.empty:
            return None
        
        # Check if Position column exists and has data
        if 'Position' not in session.laps.columns:
            return None
        
        # Get laps with position data
        position_data = []
        
        # Group by lap number and get position for each driver
        for lap_num in session.laps['LapNumber'].unique():
            lap_data = session.laps[session.laps['LapNumber'] == lap_num]
            
            for _, lap in lap_data.iterrows():
                if pd.notna(lap['Position']):
                    try:
                        position = int(float(lap['Position']))  # Convert safely
                        position_data.append({
                            'LapNumber': int(lap_num),
                            'Driver': lap['Driver'],
                            'Position': position
                        })
                    except (ValueError, TypeError):
                        continue
        
        if not position_data:
            return None
        
        return pd.DataFrame(position_data)
        
    except Exception as e:
        st.error(f"Error extracting position data: {e}")
        return None

def calculate_position_changes(position_df):
    """Calculate position changes throughout the race"""
    try:
        if position_df is None or position_df.empty:
            return None
        
        # Get session from session_state (assuming it's stored there)
        session = st.session_state.session
        
        # Use session.results for accurate start and final positions (handles penalties)
        if hasattr(session, 'results') and not session.results.empty:
            results = session.results
            start_positions = results['GridPosition'].dropna().astype(int)
            final_positions = results['Position'].dropna().astype(int)
        else:
            # Fallback to original method if results unavailable
            start_positions = position_df.groupby('Driver')['Position'].first().dropna().astype(int)
            final_positions = position_df.groupby('Driver')['Position'].last().dropna().astype(int)
        
        changes = []
        
        for driver in final_positions.index:
            try:
                start_pos = start_positions.get(driver, None)
                final_pos = final_positions.get(driver, None)
                
                if start_pos is not None and final_pos is not None:
                    positions_gained = start_pos - final_pos  # Positive = gained (lower number better)
                    
                    changes.append({
                        'Driver': driver,
                        'Start Position': start_pos,
                        'Final Position': final_pos,
                        'Positions Gained': positions_gained
                    })
            except Exception:
                continue
        
        if not changes:
            return None
        
        return pd.DataFrame(changes).sort_values('Positions Gained', ascending=False)
        
    except Exception as e:
        st.error(f"Error calculating position changes: {e}")
        return None