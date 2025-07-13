import streamlit as st
import fastf1
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import asyncio
import aiohttp
import os
from typing import Dict, List, Any
import tempfile

# Configure FastF1 cache to use temp directory for Streamlit Cloud
cache_dir = tempfile.mkdtemp()
fastf1.Cache.enable_cache(cache_dir)

class ClaudeAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
        
    async def analyze_data(self, data: str, analysis_type: str) -> str:
        """Send data to Claude for analysis"""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        prompts = {
            "lap_analysis": f"Analyze this F1 lap time data and provide insights on performance patterns, fastest sectors, and driver comparisons. Keep response under 800 words:\n\n{data}",
            "race_strategy": f"Analyze this F1 race data and provide strategic insights about pit stops, tire strategies, and race pace. Keep response under 800 words:\n\n{data}",
            "qualifying": f"Analyze this F1 qualifying data and provide insights on pole position battles, sector times, and qualifying performance. Keep response under 800 words:\n\n{data}",
            "season_trends": f"Analyze this F1 season data and identify trends, championship battles, and team performance patterns. Keep response under 800 words:\n\n{data}"
        }
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompts.get(analysis_type, f"Analyze this F1 data and keep response under 800 words:\n\n{data}")
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['content'][0]['text']
                    else:
                        return f"API Error: {response.status}. Please check your API key and try again."
        except Exception as e:
            return f"Connection Error: {str(e)}. Please check your internet connection."

class F1Dashboard:
    def __init__(self):
        self.current_year = datetime.now().year
        self.claude_analyzer = None
        
    def setup_claude(self, api_key: str):
        """Initialize Claude analyzer with API key"""
        self.claude_analyzer = ClaudeAnalyzer(api_key)
        
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def get_available_events(self, year: int) -> List[str]:
        """Get available F1 events for a given year"""
        try:
            schedule = fastf1.get_event_schedule(year)
            return schedule['EventName'].tolist()
        except Exception as e:
            st.error(f"Error fetching schedule: {e}")
            return []
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def load_session_data(self, year: int, event: str, session_type: str):
        """Load F1 session data"""
        try:
            with st.spinner(f"Loading {event} {session_type} data..."):
                session = fastf1.get_session(year, event, session_type)
                session.load()
                return session
        except Exception as e:
            st.error(f"Error loading session: {e}")
            return None
    
    def create_lap_time_chart(self, session):
        """Create lap time comparison chart"""
        laps = session.laps
        
        fig = go.Figure()
        
        drivers = laps['Driver'].unique()[:10]  # Top 10 drivers
        
        for driver in drivers:
            driver_laps = laps[laps['Driver'] == driver]
            fig.add_trace(go.Scatter(
                x=driver_laps['LapNumber'],
                y=driver_laps['LapTime'].dt.total_seconds(),
                mode='lines+markers',
                name=driver,
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title="Lap Times by Driver",
            xaxis_title="Lap Number",
            yaxis_title="Lap Time (seconds)",
            hovermode='x unified'
        )
        
        return fig
    
    def create_sector_analysis(self, session):
        """Create sector time analysis"""
        laps = session.laps
        fastest_laps = laps.pick_fastest()
        
        sector_data = []
        for _, lap in fastest_laps.iterrows():
            sector_data.append({
                'Driver': lap['Driver'],
                'Sector1': lap['Sector1Time'].total_seconds() if pd.notna(lap['Sector1Time']) else 0,
                'Sector2': lap['Sector2Time'].total_seconds() if pd.notna(lap['Sector2Time']) else 0,
                'Sector3': lap['Sector3Time'].total_seconds() if pd.notna(lap['Sector3Time']) else 0,
            })
        
        df = pd.DataFrame(sector_data)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(name='Sector 1', x=df['Driver'], y=df['Sector1']))
        fig.add_trace(go.Bar(name='Sector 2', x=df['Driver'], y=df['Sector2']))
        fig.add_trace(go.Bar(name='Sector 3', x=df['Driver'], y=df['Sector3']))
        
        fig.update_layout(
            title="Sector Times Comparison (Fastest Laps)",
            xaxis_title="Driver",
            yaxis_title="Time (seconds)",
            barmode='group'
        )
        
        return fig
    
    def create_telemetry_chart(self, session, driver1: str, driver2: str):
        """Create telemetry comparison chart"""
        try:
            lap1 = session.laps.pick_driver(driver1).pick_fastest()
            lap2 = session.laps.pick_driver(driver2).pick_fastest()
            
            tel1 = lap1.get_telemetry()
            tel2 = lap2.get_telemetry()
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=tel1['Distance'],
                y=tel1['Speed'],
                mode='lines',
                name=f"{driver1} Speed",
                line=dict(color='red', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=tel2['Distance'],
                y=tel2['Speed'],
                mode='lines',
                name=f"{driver2} Speed",
                line=dict(color='blue', width=2)
            ))
            
            fig.update_layout(
                title=f"Speed Comparison: {driver1} vs {driver2}",
                xaxis_title="Distance (m)",
                yaxis_title="Speed (km/h)",
                hovermode='x unified'
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating telemetry chart: {e}")
            return None

def main():
    st.set_page_config(
        page_title="F1 Dashboard with Claude AI", 
        page_icon="🏎️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🏎️ Formula 1 Dashboard with Claude AI Analysis")
    st.markdown("*Analyze F1 data with AI-powered insights*")
    st.markdown("---")
    
    # Initialize dashboard
    dashboard = F1Dashboard()
    
    # Sidebar for configuration
    st.sidebar.header("⚙️ Configuration")
    
    # Claude API Key input with help
    st.sidebar.markdown("### Claude API Setup")
    claude_api_key = st.sidebar.text_input(
        "Claude API Key", 
        type="password",
        help="Get your API key from https://console.anthropic.com"
    )
    
    if claude_api_key:
        dashboard.setup_claude(claude_api_key)
        st.sidebar.success("✅ Claude API connected")
    else:
        st.sidebar.info("💡 Enter your Claude API key to enable AI analysis")
    
    # F1 Session Selection
    st.sidebar.markdown("### F1 Session Selection")
    year = st.sidebar.selectbox("Year", range(2023, 2025), index=1)
    
    # Load events with caching
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
            session = dashboard.load_session_data(year, event, session_type)
            if session:
                st.session_state.session = session
                st.session_state.event_info = f"{event} {session_type} ({year})"
                st.sidebar.success(f"✅ Loaded {event} {session_type}!")
    
    # Display current session info
    if 'session' in st.session_state:
        st.sidebar.markdown("### Current Session")
        st.sidebar.info(f"📊 {st.session_state.event_info}")
    
    # Main dashboard content
    if 'session' in st.session_state:
        session = st.session_state.session
        
        # Session overview
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Laps", len(session.laps))
        with col2:
            st.metric("Drivers", len(session.laps['Driver'].unique()))
        with col3:
            fastest_lap = session.laps.pick_fastest()
            st.metric("Fastest Lap", f"{fastest_lap['LapTime']}")
        with col4:
            st.metric("Fastest Driver", fastest_lap['Driver'])
        
        st.markdown("---")
        
        # Create tabs for different analyses
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Lap Analysis", "⏱️ Sector Times", "📈 Telemetry", "🤖 Claude AI Analysis"])
        
        with tab1:
            st.header("Lap Time Analysis")
            
            # Driver selection for lap analysis
            all_drivers = session.laps['Driver'].unique().tolist()
            selected_drivers = st.multiselect(
                "Select drivers to display (max 10 for performance)", 
                all_drivers, 
                default=all_drivers[:5],
                max_selections=10
            )
            
            if selected_drivers:
                # Filter data for selected drivers
                filtered_laps = session.laps[session.laps['Driver'].isin(selected_drivers)]
                
                fig = go.Figure()
                
                for driver in selected_drivers:
                    driver_laps = filtered_laps[filtered_laps['Driver'] == driver]
                    # Convert timedelta to seconds for plotting
                    lap_times = [lap.total_seconds() for lap in driver_laps['LapTime'] if pd.notna(lap)]
                    lap_numbers = driver_laps['LapNumber'].tolist()[:len(lap_times)]
                    
                    fig.add_trace(go.Scatter(
                        x=lap_numbers,
                        y=lap_times,
                        mode='lines+markers',
                        name=driver,
                        line=dict(width=2),
                        marker=dict(size=4)
                    ))
                
                fig.update_layout(
                    title="Lap Times by Driver",
                    xaxis_title="Lap Number",
                    yaxis_title="Lap Time (seconds)",
                    hovermode='x unified',
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Please select at least one driver to display lap times.")
        
        with tab2:
            st.header("Sector Time Analysis")
            
            # Show sector analysis for fastest laps
            try:
                fastest_laps_per_driver = []
                for driver in session.laps['Driver'].unique()[:10]:  # Top 10 drivers
                    try:
                        fastest_lap = session.laps.pick_driver(driver).pick_fastest()
                        if pd.notna(fastest_lap['Sector1Time']) and pd.notna(fastest_lap['Sector2Time']) and pd.notna(fastest_lap['Sector3Time']):
                            fastest_laps_per_driver.append({
                                'Driver': driver,
                                'Sector1': fastest_lap['Sector1Time'].total_seconds(),
                                'Sector2': fastest_lap['Sector2Time'].total_seconds(),
                                'Sector3': fastest_lap['Sector3Time'].total_seconds(),
                                'Total': fastest_lap['LapTime'].total_seconds()
                            })
                    except:
                        continue
                
                if fastest_laps_per_driver:
                    df = pd.DataFrame(fastest_laps_per_driver)
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Bar(name='Sector 1', x=df['Driver'], y=df['Sector1'], marker_color='lightblue'))
                    fig.add_trace(go.Bar(name='Sector 2', x=df['Driver'], y=df['Sector2'], marker_color='lightgreen'))
                    fig.add_trace(go.Bar(name='Sector 3', x=df['Driver'], y=df['Sector3'], marker_color='lightcoral'))
                    
                    fig.update_layout(
                        title="Sector Times Comparison (Fastest Laps)",
                        xaxis_title="Driver",
                        yaxis_title="Time (seconds)",
                        barmode='group',
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show data table
                    st.markdown("### Sector Times Table")
                    st.dataframe(df.round(3), use_container_width=True)
                else:
                    st.warning("No complete sector time data available for this session.")
            except Exception as e:
                st.error(f"Error creating sector analysis: {e}")
        
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
                    else:
                        st.warning("Telemetry data not available for the selected drivers.")
                else:
                    st.warning("Please select two different drivers for comparison.")
            else:
                st.warning("At least 2 drivers are needed for telemetry comparison.")
        
        with tab4:
            st.header("Claude AI Analysis")
            
            if claude_api_key and dashboard.claude_analyzer:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    analysis_type = st.selectbox(
                        "Analysis Type",
                        ["lap_analysis", "race_strategy", "qualifying", "season_trends"],
                        format_func=lambda x: {
                            "lap_analysis": "📊 Lap Performance Analysis",
                            "race_strategy": "🏁 Race Strategy Analysis",
                            "qualifying": "⏱️ Qualifying Analysis",
                            "season_trends": "📈 Season Trends Analysis"
                        }[x]
                    )
                
                with col2:
                    if st.button("🤖 Generate AI Analysis", type="primary"):
                        with st.spinner("Claude is analyzing the F1 data..."):
                            try:
                                # Prepare data for Claude (limit to avoid token limits)
                                laps_data = session.laps[['Driver', 'LapNumber', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']].head(100)
                                
                                # Convert timedelta columns to string for JSON serialization
                                laps_data = laps_data.copy()
                                for col in ['LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time']:
                                    if col in laps_data.columns:
                                        laps_data[col] = laps_data[col].astype(str)
                                
                                data_json = laps_data.to_json(orient='records')
                                
                                # Get Claude analysis
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                analysis = loop.run_until_complete(
                                    dashboard.claude_analyzer.analyze_data(data_json, analysis_type)
                                )
                                
                                st.markdown("### 🤖 AI Analysis Results")
                                st.markdown(analysis)
                                
                                # Store analysis in session state
                                if 'analyses' not in st.session_state:
                                    st.session_state.analyses = []
                                st.session_state.analyses.append({
                                    'type': analysis_type,
                                    'event': st.session_state.event_info,
                                    'analysis': analysis,
                                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                                
                            except Exception as e:
                                st.error(f"Error during AI analysis: {e}")
                
                # Show previous analyses
                if 'analyses' in st.session_state and st.session_state.analyses:
                    st.markdown("### Previous Analyses")
                    for i, analysis in enumerate(reversed(st.session_state.analyses[-3:])):  # Show last 3
                        with st.expander(f"{analysis['type']} - {analysis['event']} ({analysis['timestamp']})"):
                            st.markdown(analysis['analysis'])
            else:
                st.warning("🔑 Please enter your Claude API key in the sidebar to enable AI analysis.")
                st.markdown("**How to get your Claude API key:**")
                st.markdown("1. Go to https://console.anthropic.com")
                st.markdown("2. Sign up or log in to your account")
                st.markdown("3. Navigate to API Keys section")
                st.markdown("4. Create a new API key")
                st.markdown("5. Copy and paste it in the sidebar")
    else:
        # Welcome screen
        st.markdown("## Welcome to F1 Dashboard! 🏎️")
        st.markdown("### Getting Started:")
        st.markdown("1. **Enter your Claude API key** in the sidebar (optional, for AI analysis)")
        st.markdown("2. **Select a year and race event** from the sidebar")
        st.markdown("3. **Choose a session type** (FP1, FP2, FP3, Q, R)")
        st.markdown("4. **Click 'Load Session Data'** to begin analyzing")
        
        st.markdown("### Features:")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("- 📊 **Lap Analysis**: Compare lap times across drivers")
            st.markdown("- ⏱️ **Sector Times**: Analyze performance by track sectors")
        with col2:
            st.markdown("- 📈 **Telemetry**: Compare speed profiles between drivers")
            st.markdown("- 🤖 **AI Analysis**: Get insights powered by Claude AI")
        
        st.info("💡 **Tip**: Start by loading a recent qualifying session or race for the best data availability!")

if __name__ == "__main__":
    main()