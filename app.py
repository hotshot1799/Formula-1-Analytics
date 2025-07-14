import streamlit as st
import fastf1
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import tempfile
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure FastF1 cache to use temp directory for Streamlit Cloud
cache_dir = tempfile.mkdtemp()
fastf1.Cache.enable_cache(cache_dir)

# Cached functions for better performance
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_events_cached(year: int) -> list:
    """Get available F1 events for a given year (cached)"""
    try:
        schedule = fastf1.get_event_schedule(year)
        return schedule['EventName'].tolist()
    except Exception as e:
        st.error(f"Error fetching schedule: {e}")
        return []

@st.cache_data(ttl=3600)  # Cache for 1 hour  
def load_session_cached(year: int, event: str, session_type: str):
    """Load F1 session data (cached)"""
    try:
        session = fastf1.get_session(year, event, session_type)
        session.load()
        return session
    except Exception as e:
        st.error(f"Error loading session: {e}")
        return None

class F1Dashboard:
    def __init__(self):
        self.current_year = datetime.now().year
        
    def get_available_events(self, year: int) -> list:
        """Get available F1 events for a given year"""
        return get_events_cached(year)
    
    def load_session_data(self, year: int, event: str, session_type: str):
        """Load F1 session data"""
        return load_session_cached(year, event, session_type)
    
    def create_lap_time_chart(self, session, selected_drivers=None):
        """Create lap time comparison chart"""
        if selected_drivers is None:
            selected_drivers = session.laps['Driver'].unique()[:10]
        
        fig = go.Figure()
        
        for driver in selected_drivers:
            driver_laps = session.laps[session.laps['Driver'] == driver]
            
            # Filter out invalid lap times
            valid_laps = driver_laps[driver_laps['LapTime'].notna()]
            
            if not valid_laps.empty:
                lap_times = [lap.total_seconds() for lap in valid_laps['LapTime']]
                lap_numbers = valid_laps['LapNumber'].tolist()
                
                fig.add_trace(go.Scatter(
                    x=lap_numbers,
                    y=lap_times,
                    mode='lines+markers',
                    name=driver,
                    line=dict(width=2),
                    marker=dict(size=4),
                    hovertemplate=f'<b>{driver}</b><br>Lap: %{{x}}<br>Time: %{{y:.3f}}s<extra></extra>'
                ))
        
        fig.update_layout(
            title="Lap Times by Driver",
            xaxis_title="Lap Number",
            yaxis_title="Lap Time (seconds)",
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    def create_sector_analysis(self, session):
        """Create sector time analysis"""
        fastest_laps_per_driver = []
        
        for driver in session.laps['Driver'].unique():
            try:
                fastest_lap = session.laps.pick_driver(driver).pick_fastest()
                if (pd.notna(fastest_lap['Sector1Time']) and 
                    pd.notna(fastest_lap['Sector2Time']) and 
                    pd.notna(fastest_lap['Sector3Time'])):
                    
                    fastest_laps_per_driver.append({
                        'Driver': driver,
                        'Sector1': fastest_lap['Sector1Time'].total_seconds(),
                        'Sector2': fastest_lap['Sector2Time'].total_seconds(),
                        'Sector3': fastest_lap['Sector3Time'].total_seconds(),
                        'Total': fastest_lap['LapTime'].total_seconds()
                    })
            except:
                continue
        
        if not fastest_laps_per_driver:
            return None
            
        df = pd.DataFrame(fastest_laps_per_driver)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Sector 1', 
            x=df['Driver'], 
            y=df['Sector1'], 
            marker_color='#FF6B6B'
        ))
        fig.add_trace(go.Bar(
            name='Sector 2', 
            x=df['Driver'], 
            y=df['Sector2'], 
            marker_color='#4ECDC4'
        ))
        fig.add_trace(go.Bar(
            name='Sector 3', 
            x=df['Driver'], 
            y=df['Sector3'], 
            marker_color='#45B7D1'
        ))
        
        fig.update_layout(
            title="Sector Times Comparison (Fastest Laps)",
            xaxis_title="Driver",
            yaxis_title="Time (seconds)",
            barmode='group',
            height=500
        )
        
        return fig, df
    
    def create_telemetry_chart(self, session, driver1: str, driver2: str):
        """Create telemetry comparison chart"""
        try:
            lap1 = session.laps.pick_driver(driver1).pick_fastest()
            lap2 = session.laps.pick_driver(driver2).pick_fastest()
            
            tel1 = lap1.get_telemetry()
            tel2 = lap2.get_telemetry()
            
            fig = go.Figure()
            
            # Speed comparison
            fig.add_trace(go.Scatter(
                x=tel1['Distance'],
                y=tel1['Speed'],
                mode='lines',
                name=f"{driver1} Speed",
                line=dict(color='#FF6B6B', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=tel2['Distance'],
                y=tel2['Speed'],
                mode='lines',
                name=f"{driver2} Speed",
                line=dict(color='#4ECDC4', width=2)
            ))
            
            fig.update_layout(
                title=f"Speed Comparison: {driver1} vs {driver2}",
                xaxis_title="Distance (m)",
                yaxis_title="Speed (km/h)",
                hovermode='x unified',
                height=500
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating telemetry chart: {e}")
            return None
    
    def create_position_chart(self, session):
        """Create position changes throughout the race"""
        if session.session_info['Type'] != 'R':  # Only for race sessions
            return None
            
        try:
            # Get position data for each lap
            position_data = []
            
            for lap_num in range(1, session.laps['LapNumber'].max() + 1):
                lap_data = session.laps[session.laps['LapNumber'] == lap_num]
                for _, lap in lap_data.iterrows():
                    if pd.notna(lap['Position']):
                        position_data.append({
                            'LapNumber': lap_num,
                            'Driver': lap['Driver'],
                            'Position': lap['Position']
                        })
            
            if not position_data:
                return None
                
            df = pd.DataFrame(position_data)
            
            fig = go.Figure()
            
            for driver in df['Driver'].unique()[:10]:  # Top 10 for readability
                driver_data = df[df['Driver'] == driver]
                fig.add_trace(go.Scatter(
                    x=driver_data['LapNumber'],
                    y=driver_data['Position'],
                    mode='lines+markers',
                    name=driver,
                    line=dict(width=2),
                    marker=dict(size=4)
                ))
            
            fig.update_layout(
                title="Position Changes Throughout the Race",
                xaxis_title="Lap Number",
                yaxis_title="Position",
                yaxis=dict(autorange='reversed'),  # Lower position number at top
                height=500
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating position chart: {e}")
            return None
    
    def get_session_statistics(self, session):
        """Get basic session statistics"""
        stats = {}
        
        try:
            # Basic info
            stats['total_laps'] = len(session.laps)
            stats['total_drivers'] = len(session.laps['Driver'].unique())
            
            # Fastest lap
            fastest_lap = session.laps.pick_fastest()
            stats['fastest_lap_time'] = str(fastest_lap['LapTime'])
            stats['fastest_lap_driver'] = fastest_lap['Driver']
            
            # Average lap time
            valid_laps = session.laps[session.laps['LapTime'].notna()]
            if not valid_laps.empty:
                avg_seconds = valid_laps['LapTime'].dt.total_seconds().mean()
                stats['average_lap_time'] = f"{avg_seconds:.3f}s"
            else:
                stats['average_lap_time'] = "N/A"
            
            return stats
            
        except Exception as e:
            st.error(f"Error calculating statistics: {e}")
            return {}

def main():
    st.set_page_config(
        page_title="F1 Analytics Dashboard", 
        page_icon="🏎️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🏎️ Formula 1 Analytics Dashboard")
    st.markdown("*Real-time F1 data analysis and visualization*")
    st.markdown("---")
    
    # Initialize dashboard
    dashboard = F1Dashboard()
    
    # Sidebar for configuration
    st.sidebar.header("⚙️ Session Selection")
    
    # Year selection
    year = st.sidebar.selectbox("Year", range(2023, 2025), index=1)
    
    # Load events
    with st.spinner("Loading F1 schedule..."):
        events = dashboard.get_available_events(year)
    
    if events:
        event = st.sidebar.selectbox("Race Event", events)
        session_type = st.sidebar.selectbox(
            "Session", 
            ["FP1", "FP2", "FP3", "Q", "R"],
            help="FP=Free Practice, Q=Qualifying, R=Race"
        )
        
        # Load session data button
        if st.sidebar.button("🔄 Load Session Data", type="primary"):
            with st.spinner(f"Loading {event} {session_type} data..."):
                session = dashboard.load_session_data(year, event, session_type)
                if session:
                    st.session_state.session = session
                    st.session_state.event_info = f"{event} {session_type} ({year})"
                    st.sidebar.success(f"✅ Data loaded successfully!")
                else:
                    st.sidebar.error("❌ Failed to load session data")
    
    # Display current session info
    if 'session' in st.session_state:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Current Session")
        st.sidebar.info(f"📊 {st.session_state.event_info}")
    
    # Main dashboard content
    if 'session' in st.session_state:
        session = st.session_state.session
        
        # Get session statistics
        stats = dashboard.get_session_statistics(session)
        
        # Session overview metrics
        if stats:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Laps", stats.get('total_laps', 0))
            with col2:
                st.metric("Drivers", stats.get('total_drivers', 0))
            with col3:
                st.metric("Fastest Lap", stats.get('fastest_lap_time', 'N/A'))
            with col4:
                st.metric("Fastest Driver", stats.get('fastest_lap_driver', 'N/A'))
        
        st.markdown("---")
        
        # Create tabs for different analyses
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Lap Analysis", 
            "⏱️ Sector Times", 
            "📈 Telemetry", 
            "🏁 Positions",
            "📋 Data Table"
        ])
        
        with tab1:
            st.header("Lap Time Analysis")
            
            # Driver selection for lap analysis
            all_drivers = session.laps['Driver'].unique().tolist()
            selected_drivers = st.multiselect(
                "Select drivers to display (max 10 for performance)", 
                all_drivers, 
                default=all_drivers[:5] if len(all_drivers) >= 5 else all_drivers,
                max_selections=10
            )
            
            if selected_drivers:
                fig = dashboard.create_lap_time_chart(session, selected_drivers)
                st.plotly_chart(fig, use_container_width=True)
                
                # Lap time statistics
                st.subheader("Lap Time Statistics")
                lap_stats = []
                for driver in selected_drivers:
                    driver_laps = session.laps[session.laps['Driver'] == driver]
                    valid_laps = driver_laps[driver_laps['LapTime'].notna()]
                    
                    if not valid_laps.empty:
                        lap_times = valid_laps['LapTime'].dt.total_seconds()
                        lap_stats.append({
                            'Driver': driver,
                            'Best Lap': f"{lap_times.min():.3f}s",
                            'Average Lap': f"{lap_times.mean():.3f}s",
                            'Worst Lap': f"{lap_times.max():.3f}s",
                            'Total Laps': len(valid_laps),
                            'Std Dev': f"{lap_times.std():.3f}s"
                        })
                
                if lap_stats:
                    df_stats = pd.DataFrame(lap_stats)
                    st.dataframe(df_stats, use_container_width=True)
            else:
                st.warning("Please select at least one driver to display lap times.")
        
        with tab2:
            st.header("Sector Time Analysis")
            
            result = dashboard.create_sector_analysis(session)
            if result:
                fig, df = result
                st.plotly_chart(fig, use_container_width=True)
                
                # Show data table
                st.subheader("Sector Times Table")
                st.dataframe(df.round(3), use_container_width=True)
                
                # Sector analysis insights
                st.subheader("Sector Analysis")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    fastest_s1 = df.loc[df['Sector1'].idxmin()]
                    st.metric("Fastest Sector 1", fastest_s1['Driver'], f"{fastest_s1['Sector1']:.3f}s")
                
                with col2:
                    fastest_s2 = df.loc[df['Sector2'].idxmin()]
                    st.metric("Fastest Sector 2", fastest_s2['Driver'], f"{fastest_s2['Sector2']:.3f}s")
                
                with col3:
                    fastest_s3 = df.loc[df['Sector3'].idxmin()]
                    st.metric("Fastest Sector 3", fastest_s3['Driver'], f"{fastest_s3['Sector3']:.3f}s")
            else:
                st.warning("No complete sector time data available for this session.")
        
        with tab3:
            st.header("Telemetry Comparison")
            
            available_drivers = session.laps['Driver'].unique().tolist()
            
            if len(available_drivers) >= 2:
                col1, col2 = st.columns(2)
                
                with col1:
                    driver1 = st.selectbox("Driver 1", available_drivers, key="driver1")
                with col2:
                    driver2 = st.selectbox("Driver 2", available_drivers, key="driver2", index=1)
                
                if driver1 != driver2:
                    fig = dashboard.create_telemetry_chart(session, driver1, driver2)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Telemetry insights
                        try:
                            lap1 = session.laps.pick_driver(driver1).pick_fastest()
                            lap2 = session.laps.pick_driver(driver2).pick_fastest()
                            
                            tel1 = lap1.get_telemetry()
                            tel2 = lap2.get_telemetry()
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(f"{driver1} Max Speed", f"{tel1['Speed'].max():.1f} km/h")
                                st.metric(f"{driver1} Avg Speed", f"{tel1['Speed'].mean():.1f} km/h")
                            
                            with col2:
                                st.metric(f"{driver2} Max Speed", f"{tel2['Speed'].max():.1f} km/h")
                                st.metric(f"{driver2} Avg Speed", f"{tel2['Speed'].mean():.1f} km/h")
                        except:
                            pass
                    else:
                        st.warning("Telemetry data not available for the selected drivers.")
                else:
                    st.warning("Please select two different drivers for comparison.")
            else:
                st.warning("At least 2 drivers are needed for telemetry comparison.")
        
        with tab4:
            st.header("Position Changes")
            
            if session.session_info['Type'] == 'R':  # Race session
                fig = dashboard.create_position_chart(session)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Starting grid vs finishing positions
                    try:
                        start_positions = session.laps[session.laps['LapNumber'] == 1][['Driver', 'Position']].dropna()
                        final_positions = session.laps.groupby('Driver')['Position'].last().dropna()
                        
                        if not start_positions.empty and not final_positions.empty:
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
                            
                            if position_changes:
                                df_changes = pd.DataFrame(position_changes)
                                df_changes = df_changes.sort_values('Positions Gained', ascending=False)
                                
                                st.subheader("Position Changes Summary")
                                st.dataframe(df_changes, use_container_width=True)
                    except:
                        pass
                else:
                    st.warning("Position data not available for this session.")
            else:
                st.info("Position tracking is only available for race sessions.")
        
        with tab5:
            st.header("Session Data")
            
            # Raw lap data
            st.subheader("Lap Data")
            lap_data = session.laps[['Driver', 'LapNumber', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 'SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST']].copy()
            
            # Convert timedelta columns to string for display
            time_columns = ['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']
            for col in time_columns:
                if col in lap_data.columns:
                    lap_data[col] = lap_data[col].astype(str)
            
            st.dataframe(lap_data, use_container_width=True)
            
            # Download data as CSV
            csv = lap_data.to_csv(index=False)
            st.download_button(
                label="📥 Download lap data as CSV",
                data=csv,
                file_name=f"{st.session_state.event_info.replace(' ', '_')}_lap_data.csv",
                mime='text/csv',
            )
    else:
        # Welcome screen
        st.markdown("## Welcome to F1 Analytics Dashboard! 🏎️")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Getting Started:")
            st.markdown("1. **Select a year** from the sidebar (2023-2024)")
            st.markdown("2. **Choose a race event** from the dropdown")
            st.markdown("3. **Pick a session type:**")
            st.markdown("   - **FP1, FP2, FP3**: Free Practice sessions")
            st.markdown("   - **Q**: Qualifying session")
            st.markdown("   - **R**: Race session")
            st.markdown("4. **Click 'Load Session Data'** to start analyzing")
            
            st.markdown("### Dashboard Features:")
            st.markdown("- 📊 **Lap Analysis**: Compare lap times and performance")
            st.markdown("- ⏱️ **Sector Times**: Detailed sector-by-sector analysis")
            st.markdown("- 📈 **Telemetry**: Speed profiles and technical data")
            st.markdown("- 🏁 **Positions**: Race position changes (race sessions only)")
            st.markdown("- 📋 **Data Export**: Download data as CSV files")
        
        with col2:
            st.markdown("### Recent Races")
            st.markdown("**Recommended sessions:**")
            st.markdown("- 🏆 **Race sessions** for complete data")
            st.markdown("- ⏱️ **Qualifying** for best lap comparisons")
            st.markdown("- 🔧 **FP3** for representative practice data")
            
            st.info("💡 **Pro Tip**: Start with a recent race weekend for the best data availability and most exciting analysis!")
        
        st.markdown("---")
        st.markdown("*Powered by FastF1 and Streamlit*")

if __name__ == "__main__":
    main()