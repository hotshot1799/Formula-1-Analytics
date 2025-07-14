"""
Chart creation functions for F1 Analytics Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

def create_lap_times_chart(session, selected_drivers):
    """Create optimized lap times chart"""
    fig = go.Figure()
    
    # Limit drivers for performance
    drivers_to_show = selected_drivers[:10]
    
    for i, driver in enumerate(drivers_to_show):
        driver_laps = session.laps[session.laps['Driver'] == driver]
        valid_laps = driver_laps[driver_laps['LapTime'].notna()]
        
        if not valid_laps.empty:
            lap_times = [lap.total_seconds() for lap in valid_laps['LapTime']]
            lap_numbers = valid_laps['LapNumber'].tolist()
            
            # Use different colors for better distinction
            color = px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)]
            
            fig.add_trace(go.Scatter(
                x=lap_numbers,
                y=lap_times,
                mode='lines+markers',
                name=driver,
                line=dict(width=2, color=color),
                marker=dict(size=3),
                hovertemplate=f'<b>{driver}</b><br>Lap: %{{x}}<br>Time: %{{y:.3f}}s<extra></extra>'
            ))
    
    fig.update_layout(
        title="Lap Times Analysis",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        hovermode='x unified',
        height=500,
        showlegend=True
    )
    
    return fig

def create_sector_analysis_chart(session):
    """Create sector analysis chart"""
    fastest_laps_data = []
    
    # Get fastest lap for each driver
    for driver in session.laps['Driver'].unique():
        try:
            fastest_lap = session.laps.pick_driver(driver).pick_fastest()
            if (pd.notna(fastest_lap['Sector1Time']) and 
                pd.notna(fastest_lap['Sector2Time']) and 
                pd.notna(fastest_lap['Sector3Time'])):
                
                fastest_laps_data.append({
                    'Driver': driver,
                    'Sector1': fastest_lap['Sector1Time'].total_seconds(),
                    'Sector2': fastest_lap['Sector2Time'].total_seconds(),
                    'Sector3': fastest_lap['Sector3Time'].total_seconds(),
                    'Total': fastest_lap['LapTime'].total_seconds()
                })
        except:
            continue
    
    if not fastest_laps_data:
        return None, None
    
    df = pd.DataFrame(fastest_laps_data)
    
    # Create sector comparison chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Sector 1', 
        x=df['Driver'], 
        y=df['Sector1'], 
        marker_color='#FF6B6B',
        hovertemplate='<b>%{x}</b><br>Sector 1: %{y:.3f}s<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Sector 2', 
        x=df['Driver'], 
        y=df['Sector2'], 
        marker_color='#4ECDC4',
        hovertemplate='<b>%{x}</b><br>Sector 2: %{y:.3f}s<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='Sector 3', 
        x=df['Driver'], 
        y=df['Sector3'], 
        marker_color='#45B7D1',
        hovertemplate='<b>%{x}</b><br>Sector 3: %{y:.3f}s<extra></extra>'
    ))
    
    fig.update_layout(
        title="Sector Times Comparison (Fastest Laps)",
        xaxis_title="Driver",
        yaxis_title="Time (seconds)",
        barmode='group',
        height=500
    )
    
    return fig, df

def create_telemetry_chart(session, driver1, driver2):
    """Create advanced telemetry comparison chart"""
    try:
        # Get fastest laps for both drivers
        lap1 = session.laps.pick_driver(driver1).pick_fastest()
        lap2 = session.laps.pick_driver(driver2).pick_fastest()
        
        # Get telemetry data
        tel1 = lap1.get_telemetry()
        tel2 = lap2.get_telemetry()
        
        # Create subplots for multiple telemetry metrics
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=['Speed Comparison', 'Throttle vs Brake', 'Gear Changes'],
            vertical_spacing=0.08,
            shared_xaxes=True
        )
        
        # Speed comparison
        fig.add_trace(
            go.Scatter(x=tel1['Distance'], y=tel1['Speed'], 
                      name=f"{driver1} Speed", line=dict(color='#FF6B6B', width=2)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=tel2['Distance'], y=tel2['Speed'], 
                      name=f"{driver2} Speed", line=dict(color='#4ECDC4', width=2)),
            row=1, col=1
        )
        
        # Throttle and Brake
        if 'Throttle' in tel1.columns and 'Brake' in tel1.columns:
            fig.add_trace(
                go.Scatter(x=tel1['Distance'], y=tel1['Throttle'], 
                          name=f"{driver1} Throttle", line=dict(color='#FF6B6B', dash='dot')),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel1['Distance'], y=tel1['Brake'], 
                          name=f"{driver1} Brake", line=dict(color='#FF0000', dash='dash')),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel2['Distance'], y=tel2['Throttle'], 
                          name=f"{driver2} Throttle", line=dict(color='#4ECDC4', dash='dot')),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel2['Distance'], y=tel2['Brake'], 
                          name=f"{driver2} Brake", line=dict(color='#0000FF', dash='dash')),
                row=2, col=1
            )
        
        # Gear changes
        if 'nGear' in tel1.columns:
            fig.add_trace(
                go.Scatter(x=tel1['Distance'], y=tel1['nGear'], 
                          name=f"{driver1} Gear", mode='lines', line=dict(color='#FF6B6B')),
                row=3, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel2['Distance'], y=tel2['nGear'], 
                          name=f"{driver2} Gear", mode='lines', line=dict(color='#4ECDC4')),
                row=3, col=1
            )
        
        fig.update_layout(height=800, title=f"Telemetry Comparison: {driver1} vs {driver2}")
        fig.update_xaxes(title_text="Distance (m)", row=3, col=1)
        fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
        fig.update_yaxes(title_text="Input %", row=2, col=1)
        fig.update_yaxes(title_text="Gear", row=3, col=1)
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating telemetry chart: {e}")
        return None

def create_position_tracking_chart(session):
    """Create position tracking chart for race sessions"""
    if session.session_info['Type'] != 'R':
        return None, None
    
    try:
        # Get position data for each lap
        position_data = []
        
        for lap_num in range(1, min(session.laps['LapNumber'].max() + 1, 71)):  # Limit to 70 laps
            lap_data = session.laps[session.laps['LapNumber'] == lap_num]
            for _, lap in lap_data.iterrows():
                if pd.notna(lap['Position']):
                    position_data.append({
                        'LapNumber': lap_num,
                        'Driver': lap['Driver'],
                        'Position': lap['Position']
                    })
        
        if not position_data:
            return None, None
        
        df = pd.DataFrame(position_data)
        
        # Create position tracking chart
        fig = go.Figure()
        
        # Show top 10 drivers for readability
        top_drivers = df.groupby('Driver')['Position'].min().sort_values().head(10).index
        
        for i, driver in enumerate(top_drivers):
            driver_data = df[df['Driver'] == driver]
            color = px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)]
            
            fig.add_trace(go.Scatter(
                x=driver_data['LapNumber'],
                y=driver_data['Position'],
                mode='lines+markers',
                name=driver,
                line=dict(width=2, color=color),
                marker=dict(size=3)
            ))
        
        fig.update_layout(
            title="Position Changes Throughout the Race",
            xaxis_title="Lap Number",
            yaxis_title="Position",
            yaxis=dict(autorange='reversed'),  # Lower position number at top
            height=500
        )
        
        # Calculate position changes
        start_positions = df[df['LapNumber'] == 1][['Driver', 'Position']].dropna()
        final_positions = df.groupby('Driver')['Position'].last().dropna()
        
        position_changes = []
        for _, row in start_positions.iterrows():
            driver = row['Driver']
            start_pos = row['Position']
            if driver in final_positions.index:
                final_pos = final_positions[driver]
                change = start_pos - final_pos  # Positive = gained positions
                position_changes.append({
                    'Driver': driver,
                    'Start Position': int(start_pos),
                    'Final Position': int(final_pos),
                    'Positions Gained': int(change)
                })
        
        changes_df = pd.DataFrame(position_changes).sort_values('Positions Gained', ascending=False)
        
        return fig, changes_df
        
    except Exception as e:
        st.error(f"Error creating position chart: {e}")
        return None, None

def create_speed_trace_chart(session, drivers):
    """Create speed trace chart for track analysis"""
    try:
        fig = go.Figure()
        
        for i, driver in enumerate(drivers[:5]):  # Limit to 5 drivers for performance
            try:
                fastest_lap = session.laps.pick_driver(driver).pick_fastest()
                telemetry = fastest_lap.get_telemetry()
                
                if 'Speed' in telemetry.columns and 'Distance' in telemetry.columns:
                    color = px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)]
                    
                    fig.add_trace(go.Scatter(
                        x=telemetry['Distance'],
                        y=telemetry['Speed'],
                        mode='lines',
                        name=driver,
                        line=dict(width=2, color=color),
                        hovertemplate=f'<b>{driver}</b><br>Distance: %{{x:.0f}}m<br>Speed: %{{y:.1f}} km/h<extra></extra>'
                    ))
            except:
                continue
        
        fig.update_layout(
            title="Speed Trace Comparison (Fastest Laps)",
            xaxis_title="Track Distance (m)",
            yaxis_title="Speed (km/h)",
            height=500,
            hovermode='x unified'
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating speed trace: {e}")
        return None