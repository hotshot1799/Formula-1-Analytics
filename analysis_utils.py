"""
Analysis utility functions for F1 Analytics Dashboard
"""
import pandas as pd
import streamlit as st

def calculate_lap_statistics(session, selected_drivers):
    """Calculate detailed lap statistics for selected drivers"""
    lap_stats = []
    
    for driver in selected_drivers:
        driver_laps = session.laps[session.laps['Driver'] == driver]
        valid_laps = driver_laps[driver_laps['LapTime'].notna()]
        
        if not valid_laps.empty:
            lap_times = valid_laps['LapTime'].dt.total_seconds()
            lap_stats.append({
                'Driver': driver,
                'Best Lap': f"{lap_times.min():.3f}s",
                'Average': f"{lap_times.mean():.3f}s",
                'Worst Lap': f"{lap_times.max():.3f}s",
                'Total Laps': len(valid_laps),
                'Consistency': f"{lap_times.std():.3f}s"
            })
    
    return pd.DataFrame(lap_stats) if lap_stats else None

def get_fastest_sector_times(df):
    """Get fastest times for each sector"""
    if df is None or df.empty:
        return None, None, None
    
    fastest_s1 = df.loc[df['Sector1'].idxmin()]
    fastest_s2 = df.loc[df['Sector2'].idxmin()]
    fastest_s3 = df.loc[df['Sector3'].idxmin()]
    
    return fastest_s1, fastest_s2, fastest_s3

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
    """Prepare data for export"""
    # Select columns to display
    available_cols = ['Driver', 'LapNumber', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 
                     'Position', 'SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST']
    display_cols = [col for col in available_cols if col in session.laps.columns]
    
    lap_data = session.laps[display_cols].copy()
    
    # Convert timedelta columns for display
    time_cols = ['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']
    for col in time_cols:
        if col in lap_data.columns:
            lap_data[col] = lap_data[col].astype(str)
    
    return lap_data

def format_session_info(stats):
    """Format session information for display"""
    info_text = ""
    
    if stats.get('track_name') and stats.get('max_speed'):
        info_text = f"**📍 {stats.get('track_name')}** | **⚡ Max Speed: {stats.get('max_speed')}**"
    elif stats.get('track_name'):
        info_text = f"**📍 {stats.get('track_name')}**"
    
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