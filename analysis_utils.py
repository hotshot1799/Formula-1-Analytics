"""
Analysis utility functions for F1 Analytics Dashboard
Fixed lap time formatting and position tracking
"""
import pandas as pd
import streamlit as st

def session_cache(func):
    """Cache within the current session only"""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = f"{func.__name__}_{'_'.join(str(id(a)) for a in args)}"
        
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
    """Safely extract position data from session with proper driver identification"""
    try:
        if not hasattr(session, 'laps') or session.laps.empty:
            return None
        
        # Check if Position column exists and has data
        if 'Position' not in session.laps.columns:
            return None
        
        # Get laps with position data
        position_data = []
        
        # Create driver mapping from driver number to driver code/name
        driver_mapping = {}
        
        # Try to get driver info from session results first
        if hasattr(session, 'results') and not session.results.empty:
            try:
                for _, row in session.results.iterrows():
                    if pd.notna(row.get('DriverNumber')) and pd.notna(row.get('Abbreviation')):
                        driver_num = str(int(row['DriverNumber']))
                        driver_mapping[driver_num] = row['Abbreviation']
                    # Also map abbreviation to itself
                    if pd.notna(row.get('Abbreviation')):
                        driver_mapping[row['Abbreviation']] = row['Abbreviation']
            except:
                pass
        
        # If no results mapping, try to extract from session.laps
        if not driver_mapping and hasattr(session, 'laps'):
            try:
                # Check if we have both DriverNumber and Driver columns
                if 'DriverNumber' in session.laps.columns and 'Driver' in session.laps.columns:
                    driver_pairs = session.laps[['DriverNumber', 'Driver']].drop_duplicates()
                    for _, row in driver_pairs.iterrows():
                        if pd.notna(row['DriverNumber']) and pd.notna(row['Driver']):
                            driver_num = str(int(row['DriverNumber']))
                            driver_mapping[driver_num] = row['Driver']
                            # Also map driver code to itself
                            driver_mapping[row['Driver']] = row['Driver']
            except:
                pass
        
        # Fallback: use common F1 driver number to code mapping
        if not driver_mapping:
            common_driver_numbers = {
                '1': 'VER', '11': 'PER', '44': 'HAM', '63': 'RUS',
                '16': 'LEC', '55': 'SAI', '4': 'NOR', '81': 'PIA',
                '14': 'ALO', '18': 'STR', '31': 'OCO', '10': 'GAS',
                '22': 'TSU', '3': 'RIC', '23': 'ALB', '2': 'SAR',
                '20': 'MAG', '27': 'HUL', '77': 'BOT', '24': 'ZHO',
                '40': 'LAW', '43': 'COL', '50': 'BEA'
            }
            driver_mapping.update(common_driver_numbers)
        
        # Group by lap number and get position for each driver
        for lap_num in session.laps['LapNumber'].unique():
            lap_data = session.laps[session.laps['LapNumber'] == lap_num]
            
            for _, lap in lap_data.iterrows():
                if pd.notna(lap['Position']):
                    try:
                        position = int(float(lap['Position']))
                        
                        # Get driver identifier - prefer Driver column over DriverNumber
                        driver_id = None
                        if 'Driver' in lap and pd.notna(lap['Driver']):
                            driver_id = lap['Driver']
                        elif 'DriverNumber' in lap and pd.notna(lap['DriverNumber']):
                            driver_num = str(int(lap['DriverNumber']))
                            driver_id = driver_mapping.get(driver_num, driver_num)
                        
                        if driver_id:
                            position_data.append({
                                'LapNumber': int(lap_num),
                                'Driver': driver_id,
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

@session_cache
def calculate_position_changes(position_df):
    """Calculate position changes throughout the race using starting grid positions"""
    try:
        if position_df is None or position_df.empty:
            return None
        
        # Get session from session_state
        session = st.session_state.session
        
        # Create enhanced driver name mapping
        driver_name_mapping = {}
        driver_full_name_mapping = {}
        
        # Try to get driver info from session.results
        if hasattr(session, 'results') and not session.results.empty:
            try:
                for _, row in session.results.iterrows():
                    # Map driver numbers to abbreviations
                    if pd.notna(row.get('DriverNumber')) and pd.notna(row.get('Abbreviation')):
                        driver_num = str(int(row['DriverNumber']))
                        driver_name_mapping[driver_num] = row['Abbreviation']
                    
                    # Map abbreviations to full names
                    if pd.notna(row.get('Abbreviation')):
                        driver_code = row['Abbreviation']
                        driver_name_mapping[driver_code] = driver_code
                        
                        if pd.notna(row.get('FullName')):
                            driver_full_name_mapping[driver_code] = row['FullName']
            except:
                pass
        
        # Enhanced fallback mapping with full names
        if not driver_name_mapping:
            driver_mapping_complete = {
                '1': 'VER', '11': 'PER', '44': 'HAM', '63': 'RUS',
                '16': 'LEC', '55': 'SAI', '4': 'NOR', '81': 'PIA',
                '14': 'ALO', '18': 'STR', '31': 'OCO', '10': 'GAS',
                '22': 'TSU', '3': 'RIC', '23': 'ALB', '2': 'SAR',
                '20': 'MAG', '27': 'HUL', '77': 'BOT', '24': 'ZHO',
                '40': 'LAW', '43': 'COL', '50': 'BEA'
            }
            
            full_names = {
                'VER': 'Max Verstappen', 'PER': 'Sergio Perez', 'HAM': 'Lewis Hamilton',
                'RUS': 'George Russell', 'LEC': 'Charles Leclerc', 'SAI': 'Carlos Sainz',
                'NOR': 'Lando Norris', 'PIA': 'Oscar Piastri', 'ALO': 'Fernando Alonso',
                'STR': 'Lance Stroll', 'OCO': 'Esteban Ocon', 'GAS': 'Pierre Gasly',
                'TSU': 'Yuki Tsunoda', 'RIC': 'Daniel Ricciardo', 'ALB': 'Alexander Albon',
                'SAR': 'Logan Sargeant', 'MAG': 'Kevin Magnussen', 'HUL': 'Nico Hulkenberg',
                'BOT': 'Valtteri Bottas', 'ZHO': 'Guanyu Zhou', 'LAW': 'Liam Lawson',
                'COL': 'Franco Colapinto', 'BEA': 'Ollie Bearman'
            }
            
            driver_name_mapping.update(driver_mapping_complete)
            driver_full_name_mapping.update(full_names)
            
            # Also map codes to themselves
            for code in full_names.keys():
                driver_name_mapping[code] = code
        
        # PRIORITY: Use starting grid positions from session.results
        start_positions = None
        final_positions = None
        
        if hasattr(session, 'results') and not session.results.empty:
            try:
                # Get starting grid positions (GridPosition) and final positions (Position)
                results = session.results
                
                # Create mapping from driver abbreviations to positions
                grid_positions = {}
                finish_positions = {}
                
                for _, row in results.iterrows():
                    if pd.notna(row.get('Abbreviation')):
                        driver_code = row['Abbreviation']
                        
                        # Starting grid position
                        if pd.notna(row.get('GridPosition')):
                            try:
                                grid_pos = int(row['GridPosition'])
                                grid_positions[driver_code] = grid_pos
                            except:
                                pass
                        
                        # Final race position
                        if pd.notna(row.get('Position')):
                            try:
                                final_pos = int(row['Position'])
                                finish_positions[driver_code] = final_pos
                            except:
                                pass
                
                # Convert to pandas Series for consistency
                if grid_positions:
                    start_positions = pd.Series(grid_positions)
                    st.info(f"📊 Using starting grid positions from race results")
                    
                if finish_positions:
                    final_positions = pd.Series(finish_positions)
                else:
                    # Fallback to position data from lap analysis
                    final_positions = position_df.groupby('Driver')['Position'].last().dropna().astype(int)
                    
            except Exception as e:
                st.warning(f"⚠️ Could not extract grid positions from results: {e}")
        
        # FALLBACK: Use position data if no grid positions available
        if start_positions is None:
            st.warning("⚠️ No starting grid data available - using first lap positions as fallback")
            start_positions = position_df.groupby('Driver')['Position'].first().dropna().astype(int)
        
        if final_positions is None:
            final_positions = position_df.groupby('Driver')['Position'].last().dropna().astype(int)
        
        # Calculate position changes
        changes = []
        
        # Get common drivers between start and final positions
        common_drivers = set(start_positions.index) & set(final_positions.index)
        
        for driver in common_drivers:
            try:
                start_pos = start_positions.get(driver, None)
                final_pos = final_positions.get(driver, None)
                
                if start_pos is not None and final_pos is not None:
                    positions_gained = start_pos - final_pos  # Positive = gained positions (lower number is better)
                    
                    # Get proper driver name
                    driver_code = driver_name_mapping.get(driver, driver)
                    full_name = driver_full_name_mapping.get(driver_code, driver_code)
                    
                    changes.append({
                        'Driver': driver_code,
                        'Full Name': full_name,
                        'Start Position': start_pos,
                        'Final Position': final_pos,
                        'Positions Gained': positions_gained
                    })
            except Exception as e:
                st.error(f"Error processing driver {driver}: {e}")
                continue
        
        if not changes:
            st.error("❌ No position changes could be calculated")
            return None
        
        # Sort by positions gained (most gained first)
        changes_df = pd.DataFrame(changes).sort_values('Positions Gained', ascending=False)
        
        # Add some debug info
        st.info(f"📊 Position changes calculated for {len(changes_df)} drivers")
        
        return changes_df
        
    except Exception as e:
        st.error(f"Error calculating position changes: {e}")
        return None