"""
Dynamic F1 Team Color System - Assigns colors based on session data
Add this to: team_colors.py
"""
import streamlit as st
import pandas as pd

# F1 Team Base Colors (not tied to specific drivers)
F1_TEAM_BASE_COLORS = {
    'Red Bull Racing': ['#0600EF', '#1E41FF'],           # Navy blues
    'Mercedes': ['#00D2BE', '#70F2FF'],                  # Teals
    'Ferrari': ['#DC143C', '#FF6B6B'],                   # Reds
    'McLaren': ['#FF8700', '#FFB000'],                   # Oranges
    'Aston Martin': ['#006F62', '#229971'],              # Greens
    'Alpine': ['#0090FF', '#FF87BC'],                    # Blue/Pink
    'Williams': ['#005AFF', '#4A90E2'],                  # Blues
    'Haas': ['#B6BABD', '#FF4444'],                      # Gray/Red
    'Alfa Romeo': ['#900000', '#C1272D'],                # Burgundy/Red
    'Sauber': ['#900000', '#C1272D'],                    # Burgundy/Red
    'AlphaTauri': ['#2B4562', '#5A6B7D'],               # Navy/Gray
    'RB': ['#2B4562', '#5A6B7D'],                       # Navy/Gray (AlphaTauri rebrand)
    'Kick Sauber': ['#00FF87', '#4AFF4A'],              # Green variants
}

# Generic team colors if team not recognized
GENERIC_TEAM_COLORS = [
    ['#FF6B6B', '#FF8E8E'],  # Light reds
    ['#4ECDC4', '#7EDDD8'],  # Teals
    ['#45B7D1', '#6BC5E3'],  # Blues
    ['#96CEB4', '#B8E6C1'],  # Greens
    ['#FFEAA7', '#FFE082'],  # Yellows
    ['#DDA0DD', '#E6B3E6'],  # Purples
    ['#98D8C8', '#B8E6D8'],  # Mint greens
    ['#F7DC6F', '#FCE570'],  # Golds
]

def get_dynamic_team_colors(session):
    """
    Dynamically assign team colors based on session data
    Returns a dictionary mapping driver codes to colors
    """
    driver_colors = {}
    
    try:
        # Try to get team information from session results
        if hasattr(session, 'results') and not session.results.empty:
            # Group drivers by team
            teams = {}
            
            for _, row in session.results.iterrows():
                if pd.notna(row.get('Abbreviation')) and pd.notna(row.get('TeamName')):
                    driver = row['Abbreviation']
                    team = row['TeamName']
                    
                    if team not in teams:
                        teams[team] = []
                    teams[team].append(driver)
            
            # Assign colors to teams
            team_color_index = 0
            
            for team_name, drivers in teams.items():
                # Try to match with known team colors
                team_colors = None
                
                # Look for team name matches (partial matching)
                for known_team, colors in F1_TEAM_BASE_COLORS.items():
                    if any(keyword in team_name.lower() for keyword in known_team.lower().split()):
                        team_colors = colors
                        break
                
                # Use generic colors if team not recognized
                if team_colors is None:
                    team_colors = GENERIC_TEAM_COLORS[team_color_index % len(GENERIC_TEAM_COLORS)]
                    team_color_index += 1
                
                # Assign colors to drivers (first driver gets first color, second gets second)
                for i, driver in enumerate(drivers):
                    color_index = i % len(team_colors)
                    driver_colors[driver] = team_colors[color_index]
        
        # Fallback: Use session.laps if results not available
        elif hasattr(session, 'laps') and not session.laps.empty:
            unique_drivers = session.laps['Driver'].unique()
            
            # Assign generic colors to drivers
            for i, driver in enumerate(unique_drivers):
                team_index = i // 2  # Every 2 drivers get same team colors
                color_index = i % 2   # First or second color of the team
                
                team_colors = GENERIC_TEAM_COLORS[team_index % len(GENERIC_TEAM_COLORS)]
                driver_colors[driver] = team_colors[color_index]
    
    except Exception as e:
        st.warning(f"Could not determine team colors: {e}")
        
        # Ultimate fallback - assign random colors
        if hasattr(session, 'laps') and not session.laps.empty:
            unique_drivers = session.laps['Driver'].unique()
            for i, driver in enumerate(unique_drivers):
                color_index = i % len(GENERIC_TEAM_COLORS)
                driver_colors[driver] = GENERIC_TEAM_COLORS[color_index][0]
    
    return driver_colors

def get_driver_color(driver_code, session=None):
    """Get color for a specific driver"""
    # Check if we have cached colors in session state
    if 'driver_colors' not in st.session_state and session:
        st.session_state.driver_colors = get_dynamic_team_colors(session)
    
    if 'driver_colors' in st.session_state:
        return st.session_state.driver_colors.get(driver_code, '#808080')
    
    # Fallback to generic color
    return '#808080'

def get_team_colors_for_drivers(drivers, session=None):
    """Get a list of colors for multiple drivers"""
    return [get_driver_color(driver, session) for driver in drivers]

def initialize_session_colors(session):
    """Initialize colors for the current session"""
    st.session_state.driver_colors = get_dynamic_team_colors(session)
    
    # Debug info
    if 'driver_colors' in st.session_state:
        st.sidebar.success(f"🎨 Team colors assigned for {len(st.session_state.driver_colors)} drivers")

def get_color_by_driver_number(driver_number, session=None):
    """Get color by driver number (if needed for legacy support)"""
    # This would need to be mapped through session data
    # For now, return a generic color
    return '#808080'

# Helper function to display color legend
def show_driver_color_legend():
    """Display a color legend in the sidebar"""
    if 'driver_colors' in st.session_state:
        st.sidebar.markdown("### 🎨 Driver Colors")
        
        for driver, color in st.session_state.driver_colors.items():
            st.sidebar.markdown(
                f'<div style="display: flex; align-items: center; margin: 2px 0;">'
                f'<div style="width: 20px; height: 20px; background-color: {color}; '
                f'border-radius: 3px; margin-right: 8px; border: 1px solid #ccc;"></div>'
                f'<span>{driver}</span></div>',
                unsafe_allow_html=True
            )