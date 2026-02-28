"""
Updated chart_creators.py with dynamic F1 team colors
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Import the dynamic team colors
from team_colors import get_driver_color, initialize_session_colors, show_driver_color_legend
from analysis_utils import format_lap_time

def create_lap_times_chart(session, selected_drivers):
    """Create lap times chart with dynamic F1 team colors"""
    fig = go.Figure()
    
    # Initialize colors for this session if not already done
    if 'driver_colors' not in st.session_state:
        initialize_session_colors(session)
    
    # Limit drivers for performance
    drivers_to_show = selected_drivers[:10]
    
    for i, driver in enumerate(drivers_to_show):
        try:
            driver_laps = session.laps[session.laps['Driver'] == driver]
            valid_laps = driver_laps[driver_laps['LapTime'].notna()]
            
            if not valid_laps.empty:
                lap_times = [lap.total_seconds() for lap in valid_laps['LapTime']]
                lap_numbers = valid_laps['LapNumber'].tolist()
                
                # Create hover text with proper formatting
                hover_text = [
                    f"<b>{driver}</b><br>Lap: {lap_num}<br>Time: {format_lap_time(time_sec)}"
                    for lap_num, time_sec in zip(lap_numbers, lap_times)
                ]
                
                # Use dynamic team colors
                color = get_driver_color(driver, session)
                
                fig.add_trace(go.Scatter(
                    x=lap_numbers,
                    y=lap_times,
                    mode='lines+markers',
                    name=driver,
                    line=dict(width=3, color=color),
                    marker=dict(size=4, color=color),
                    hovertemplate='%{text}<extra></extra>',
                    text=hover_text
                ))
        except Exception as e:
            continue
    
    # Format y-axis to show lap times properly
    fig.update_layout(
        title="Lap Times Analysis",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        hovermode='x unified',
        height=500,
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_sector_analysis_chart(session):
    """Create sector analysis chart with dynamic F1 team colors"""
    fastest_laps_data = []
    
    # Initialize colors for this session if not already done
    if 'driver_colors' not in st.session_state:
        initialize_session_colors(session)
    
    # Get fastest lap for each driver
    for driver in session.laps['Driver'].unique():
        try:
            fastest_lap = session.laps.pick_driver(driver).pick_fastest()
            
            # Check if sector data is available
            if (pd.notna(fastest_lap.get('Sector1Time')) and 
                pd.notna(fastest_lap.get('Sector2Time')) and 
                pd.notna(fastest_lap.get('Sector3Time'))):
                
                fastest_laps_data.append({
                    'Driver': driver,
                    'Sector1': fastest_lap['Sector1Time'].total_seconds(),
                    'Sector2': fastest_lap['Sector2Time'].total_seconds(),
                    'Sector3': fastest_lap['Sector3Time'].total_seconds(),
                    'Total': fastest_lap['LapTime'].total_seconds()
                })
        except Exception as e:
            continue
    
    if not fastest_laps_data:
        return None, None
    
    df = pd.DataFrame(fastest_laps_data)
    
    # Create sector comparison chart with team colors
    fig = go.Figure()
    
    # Add hover templates with proper time formatting and team colors
    for driver in df['Driver']:
        color = get_driver_color(driver, session)
        
        fig.add_trace(go.Bar(
            name=f'{driver} S1', 
            x=[driver], 
            y=[df.loc[df['Driver'] == driver, 'Sector1'].iloc[0]], 
            marker_color=color,
            opacity=0.8,
            width=0.25,
            offsetgroup=1,
            hovertemplate=f'<b>{driver}</b><br>Sector 1: %{{y:.3f}}s<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name=f'{driver} S2', 
            x=[driver], 
            y=[df.loc[df['Driver'] == driver, 'Sector2'].iloc[0]], 
            marker_color=color,
            opacity=0.6,
            width=0.25,
            offsetgroup=2,
            hovertemplate=f'<b>{driver}</b><br>Sector 2: %{{y:.3f}}s<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name=f'{driver} S3', 
            x=[driver], 
            y=[df.loc[df['Driver'] == driver, 'Sector3'].iloc[0]], 
            marker_color=color,
            opacity=0.4,
            width=0.25,
            offsetgroup=3,
            hovertemplate=f'<b>{driver}</b><br>Sector 3: %{{y:.3f}}s<extra></extra>'
        ))
    
    fig.update_layout(
        title="Sector Times Comparison (Fastest Laps)",
        xaxis_title="Driver",
        yaxis_title="Time (seconds)",
        barmode='group',
        height=500,
        showlegend=False,  # Hide legend as it would be too cluttered
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig, df

def create_telemetry_chart(session, driver1, driver2):
    """Create telemetry comparison chart with dynamic F1 team colors"""
    try:
        # Initialize colors for this session if not already done
        if 'driver_colors' not in st.session_state:
            initialize_session_colors(session)
        
        # Get fastest laps for both drivers
        lap1 = session.laps.pick_driver(driver1).pick_fastest()
        lap2 = session.laps.pick_driver(driver2).pick_fastest()
        
        # Get telemetry data
        tel1 = lap1.get_telemetry()
        tel2 = lap2.get_telemetry()
        
        if tel1.empty or tel2.empty:
            return None
        
        # Get team colors for both drivers
        color1 = get_driver_color(driver1, session)
        color2 = get_driver_color(driver2, session)
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=['Speed Comparison', 'Throttle vs Brake', 'Gear Changes'],
            vertical_spacing=0.08,
            shared_xaxes=True
        )
        
        # Speed comparison with team colors
        fig.add_trace(
            go.Scatter(x=tel1['Distance'], y=tel1['Speed'], 
                      name=f"{driver1} Speed", line=dict(color=color1, width=3)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=tel2['Distance'], y=tel2['Speed'], 
                      name=f"{driver2} Speed", line=dict(color=color2, width=3)),
            row=1, col=1
        )
        
        # Throttle and Brake (if available)
        if 'Throttle' in tel1.columns and 'Brake' in tel1.columns:
            fig.add_trace(
                go.Scatter(x=tel1['Distance'], y=tel1['Throttle'], 
                          name=f"{driver1} Throttle", line=dict(color=color1, dash='dot', width=2)),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel1['Distance'], y=tel1['Brake'], 
                          name=f"{driver1} Brake", line=dict(color=color1, dash='dash', width=2)),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel2['Distance'], y=tel2['Throttle'], 
                          name=f"{driver2} Throttle", line=dict(color=color2, dash='dot', width=2)),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel2['Distance'], y=tel2['Brake'], 
                          name=f"{driver2} Brake", line=dict(color=color2, dash='dash', width=2)),
                row=2, col=1
            )
        
        # Gear changes (if available)
        if 'nGear' in tel1.columns:
            fig.add_trace(
                go.Scatter(x=tel1['Distance'], y=tel1['nGear'], 
                          name=f"{driver1} Gear", mode='lines', line=dict(color=color1, width=2)),
                row=3, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel2['Distance'], y=tel2['nGear'], 
                          name=f"{driver2} Gear", mode='lines', line=dict(color=color2, width=2)),
                row=3, col=1
            )
        
        fig.update_layout(
            height=800, 
            title=f"Telemetry Comparison: {driver1} vs {driver2}",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_xaxes(title_text="Distance (m)", row=3, col=1)
        fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
        fig.update_yaxes(title_text="Input %", row=2, col=1)
        fig.update_yaxes(title_text="Gear", row=3, col=1)
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating telemetry chart: {e}")
        return None

def create_speed_trace_chart(session, drivers):
    """Create speed trace chart with dynamic F1 team colors"""
    try:
        # Initialize colors for this session if not already done
        if 'driver_colors' not in st.session_state:
            initialize_session_colors(session)
        
        fig = go.Figure()
        
        for i, driver in enumerate(drivers[:5]):  # Limit to 5 drivers
            try:
                fastest_lap = session.laps.pick_driver(driver).pick_fastest()
                telemetry = fastest_lap.get_telemetry()
                
                if not telemetry.empty and 'Speed' in telemetry.columns and 'Distance' in telemetry.columns:
                    color = get_driver_color(driver, session)
                    
                    fig.add_trace(go.Scatter(
                        x=telemetry['Distance'],
                        y=telemetry['Speed'],
                        mode='lines',
                        name=driver,
                        line=dict(width=3, color=color),
                        hovertemplate=f'<b>{driver}</b><br>Distance: %{{x:.0f}}m<br>Speed: %{{y:.1f}} km/h<extra></extra>'
                    ))
            except Exception as e:
                continue
        
        fig.update_layout(
            title="Speed Trace Comparison (Fastest Laps)",
            xaxis_title="Track Distance (m)",
            yaxis_title="Speed (km/h)",
            height=500,
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating speed trace: {e}")
        return None

