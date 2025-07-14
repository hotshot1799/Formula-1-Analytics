"""
F1 Analytics Dashboard - Main Application
Split into modular components for better performance and maintainability
"""
import streamlit as st
import pandas as pd

# Import custom modules
from data_loader import (
    get_schedule, load_session, get_session_stats, get_available_years, 
    check_session_availability, get_race_weekend_summary
)
from chart_creators import (
    create_lap_times_chart, 
    create_sector_analysis_chart, 
    create_telemetry_chart,
    create_position_tracking_chart,
    create_speed_trace_chart
)
from analysis_utils import (
    calculate_lap_statistics,
    get_fastest_sector_times,
    get_telemetry_insights,
    prepare_export_data,
    format_session_info,
    get_season_indicator
)

def setup_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="F1 Analytics Dashboard", 
        page_icon="🏎️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def render_header():
    """Render page header"""
    st.title("🏎️ Formula 1 Analytics Dashboard")
    st.markdown("*Advanced F1 telemetry and race analysis*")
    st.markdown("---")

def render_sidebar():
    """Render sidebar with session selection"""
    st.sidebar.header("⚙️ Session Selection")
    
    # Get available years dynamically
    available_years = get_available_years()
    
    if not available_years:
        st.sidebar.error("No F1 data available")
        return None, None, None, None
    
    # Year selection with dynamic list
    year = st.sidebar.selectbox(
        "Season", 
        available_years,
        help="Select F1 season"
    )
    
    # Load events
    with st.spinner("Loading schedule..."):
        events = get_schedule(year)
    
    if not events:
        st.sidebar.error(f"No events found for {year}")
        return year, None, None, None
    
    # Show season status
    current_year = 2025
    if year == current_year:
        st.sidebar.success(f"🏁 {year} Season - Live Data!")
        st.sidebar.info(f"📅 {len(events)} race weekends with data")
    elif year == 2024:
        st.sidebar.success("🏆 Complete 2024 Season!")
    else:
        st.sidebar.info(f"📚 {year} Historical Data")
    
    # Event selection with enhanced info
    event = st.sidebar.selectbox("Race Event", events)
    
    # Check available sessions for selected event
    if event:
        available_sessions = check_session_availability(year, event)
        weekend_summary = get_race_weekend_summary(year, event)
        
        # Show race weekend status
        if weekend_summary['status'] == 'completed':
            st.sidebar.success("✅ Race Weekend Complete")
        elif weekend_summary['status'] == 'qualifying_done':
            st.sidebar.info("🏁 Qualifying Done, Race Pending")
        elif weekend_summary['status'] == 'practice_only':
            st.sidebar.warning("⚠️ Practice Sessions Only")
        else:
            st.sidebar.error("❌ No Data Available")
        
        # Show available sessions
        if available_sessions:
            session_names = {
                'R': 'Race', 'Q': 'Qualifying', 'S': 'Sprint',
                'FP1': 'Free Practice 1', 'FP2': 'Free Practice 2', 'FP3': 'Free Practice 3'
            }
            available_session_names = [session_names.get(s, s) for s in available_sessions]
            st.sidebar.success(f"📊 Available: {', '.join(available_session_names)}")
        
        # Session selection - only show available sessions
        if available_sessions:
            session_options = available_sessions
        else:
            session_options = ["R", "Q", "FP3", "FP2", "FP1", "S"]
        
        session_type = st.sidebar.selectbox(
            "Session", 
            session_options,
            help="Select session type (only available sessions shown)"
        )
    else:
        session_type = st.sidebar.selectbox(
            "Session", 
            ["R", "Q", "FP3", "FP2", "FP1", "S"],
            help="Select session type"
        )
    
    # Load session data
    if st.sidebar.button("🔄 Load Session Data", type="primary"):
        with st.spinner("Loading session data..."):
            session = load_session(year, event, session_type)
            if session:
                st.session_state.session = session
                st.session_state.event_info = f"{event} {session_type} ({year})"
                st.session_state.year = year
                st.sidebar.success("✅ Data loaded!")
                
                # Show additional info for current season
                if year == current_year:
                    st.sidebar.info("📊 Live 2025 season analysis!")
            else:
                st.sidebar.error("❌ Failed to load data")
                if session_type not in (available_sessions if 'available_sessions' in locals() else []):
                    st.sidebar.warning("💡 This session may not have occurred yet")
                else:
                    st.sidebar.info("💡 Try a different session type")
    
    # Show current session info
    if 'session' in st.session_state:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Current Session")
        st.sidebar.info(f"📊 {st.session_state.event_info}")
        
        # Show session insights
        session = st.session_state.session
        if hasattr(session, 'date') and session.date:
            st.sidebar.text(f"📅 {session.date}")
    
    return year, event, session_type, events

def render_welcome_screen():
    """Render welcome screen when no session is loaded"""
    st.markdown("## Welcome to Advanced F1 Analytics! 🏎️")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🚀 Advanced Features:")
        st.markdown("- **📊 Lap Analysis** - Detailed lap time comparisons")
        st.markdown("- **⏱️ Sector Analysis** - Sector-by-sector performance")
        st.markdown("- **📈 Telemetry** - Speed, throttle, brake, gear analysis")
        st.markdown("- **🏁 Position Tracking** - Race position changes")
        st.markdown("- **🎯 Speed Traces** - Track-based speed analysis")
    
    with col2:
        st.markdown("### 📋 Getting Started:")
        st.markdown("1. Select **2025** for current season")
        st.markdown("2. Choose completed race event")
        st.markdown("3. Pick session type")
        st.markdown("4. Click 'Load Session Data'")
        st.markdown("5. Explore all analysis tabs")
    
    # Show current season info
    st.markdown("---")
    st.markdown("### 🏁 2025 Season Status")
    
    current_year = 2025
    available_years = get_available_years()
    
    if current_year in available_years:
        # Get 2025 events
        events_2025 = get_schedule(current_year)
        if events_2025:
            st.success(f"✅ **2025 Season Active** - {len(events_2025)} race weekends with data available!")
            
            # Show race weekend statuses
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**🏁 Available Race Weekends:**")
                for event in events_2025[:5]:  # Show first 5
                    summary = get_race_weekend_summary(current_year, event)
                    if summary['status'] == 'completed':
                        st.markdown(f"- ✅ **{event}** (Complete)")
                    elif summary['status'] == 'qualifying_done':
                        st.markdown(f"- 🏁 **{event}** (Qualifying Done)")
                    elif summary['status'] == 'practice_only':
                        st.markdown(f"- ⚠️ **{event}** (Practice Only)")
                
                if len(events_2025) > 5:
                    st.markdown(f"... and {len(events_2025) - 5} more weekends")
            
            with col2:
                st.markdown("**💡 Best Sessions to Analyze:**")
                st.markdown("- **Race (R)**: Complete race analysis")
                st.markdown("- **Qualifying (Q)**: Pole position battles")
                st.markdown("- **FP3**: Representative practice pace")
                st.markdown("- **Sprint (S)**: If available")
                
                st.info("🔄 **Live Season**: Data updates after each session!")
        else:
            st.warning("⚠️ 2025 season detected but no race data available yet")
    else:
        st.info("📅 2025 season data will appear when races begin")
    
    # Show other seasons
    if len(available_years) > 1:
        st.markdown("### 📚 Other Available Seasons:")
        for year in available_years:
            if year != current_year:
                events_count = len(get_schedule(year))
                if year == 2024:
                    st.markdown(f"- **{year}**: Complete season ({events_count} races) 🏆")
                else:
                    st.markdown(f"- **{year}**: Historical data ({events_count} races)")
    
    st.info("💡 **Pro Tip**: Start with completed race weekends for the most detailed analysis. Check the sidebar for race weekend status!")

def render_session_overview(session, stats):
    """Render session overview with key metrics"""
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Laps", stats.get('total_laps', 0))
    with col2:
        st.metric("Drivers", stats.get('total_drivers', 0))
    with col3:
        st.metric("Fastest Lap", stats.get('fastest_lap_time', 'N/A'))
    with col4:
        st.metric("Fastest Driver", stats.get('fastest_lap_driver', 'N/A'))
    
    # Additional session info
    info_text = format_session_info(stats)
    if info_text:
        st.markdown(info_text)
    
    # Show current season indicator
    current_year = st.session_state.get('year', 2024)
    indicator_text, indicator_type = get_season_indicator(current_year)
    
    if indicator_type == "success":
        st.success(indicator_text)
    else:
        st.info(indicator_text)

def render_lap_analysis_tab(session):
    """Render lap analysis tab"""
    st.header("Lap Time Analysis")
    
    all_drivers = session.laps['Driver'].unique().tolist()
    selected_drivers = st.multiselect(
        "Select drivers (max 10):", 
        all_drivers, 
        default=all_drivers[:5] if len(all_drivers) >= 5 else all_drivers,
        max_selections=10
    )
    
    if selected_drivers:
        fig = create_lap_times_chart(session, selected_drivers)
        st.plotly_chart(fig, use_container_width=True)
        
        # Lap statistics table
        st.subheader("Lap Time Statistics")
        lap_stats_df = calculate_lap_statistics(session, selected_drivers)
        
        if lap_stats_df is not None:
            st.dataframe(lap_stats_df, use_container_width=True)
    else:
        st.warning("Please select at least one driver to analyze")

def render_sector_analysis_tab(session):
    """Render sector analysis tab"""
    st.header("Sector Time Analysis")
    
    result = create_sector_analysis_chart(session)
    if result[0]:
        fig, df = result
        st.plotly_chart(fig, use_container_width=True)
        
        # Sector analysis insights
        fastest_s1, fastest_s2, fastest_s3 = get_fastest_sector_times(df)
        
        if fastest_s1 is not None:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Fastest Sector 1", fastest_s1['Driver'], f"{fastest_s1['Sector1']:.3f}s")
            with col2:
                st.metric("Fastest Sector 2", fastest_s2['Driver'], f"{fastest_s2['Sector2']:.3f}s")
            with col3:
                st.metric("Fastest Sector 3", fastest_s3['Driver'], f"{fastest_s3['Sector3']:.3f}s")
        
        st.subheader("Detailed Sector Times")
        st.dataframe(df.round(3), use_container_width=True)
    else:
        st.warning("No sector time data available for this session")

def render_telemetry_tab(session):
    """Render telemetry analysis tab"""
    st.header("Advanced Telemetry Analysis")
    
    available_drivers = session.laps['Driver'].unique().tolist()
    
    if len(available_drivers) >= 2:
        col1, col2 = st.columns(2)
        with col1:
            driver1 = st.selectbox("Driver 1", available_drivers, key="tel_driver1")
        with col2:
            driver2 = st.selectbox("Driver 2", available_drivers, key="tel_driver2", index=1)
        
        if driver1 != driver2:
            fig = create_telemetry_chart(session, driver1, driver2)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                # Telemetry insights
                insights = get_telemetry_insights(session, driver1, driver2)
                if insights:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"{driver1} Telemetry")
                        st.metric("Max Speed", f"{insights[driver1]['max_speed']:.1f} km/h")
                        st.metric("Avg Speed", f"{insights[driver1]['avg_speed']:.1f} km/h")
                        if insights[driver1]['avg_throttle']:
                            st.metric("Avg Throttle", f"{insights[driver1]['avg_throttle']:.1f}%")
                    
                    with col2:
                        st.subheader(f"{driver2} Telemetry")
                        st.metric("Max Speed", f"{insights[driver2]['max_speed']:.1f} km/h")
                        st.metric("Avg Speed", f"{insights[driver2]['avg_speed']:.1f} km/h")
                        if insights[driver2]['avg_throttle']:
                            st.metric("Avg Throttle", f"{insights[driver2]['avg_throttle']:.1f}%")
            else:
                st.warning("Telemetry data not available for selected drivers")
        else:
            st.warning("Please select two different drivers")
    else:
        st.warning("Need at least 2 drivers for telemetry comparison")

def render_position_tracking_tab(session):
    """Render position tracking tab"""
    st.header("Race Position Tracking")
    
    if session.session_info['Type'] == 'R':
        result = create_position_tracking_chart(session)
        if result[0]:
            fig, changes_df = result
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Position Changes Summary")
            st.dataframe(changes_df, use_container_width=True)
        else:
            st.warning("Position data not available")
    else:
        st.info("Position tracking is only available for race sessions")

def render_speed_traces_tab(session):
    """Render speed traces tab"""
    st.header("Speed Trace Analysis")
    
    trace_drivers = st.multiselect(
        "Select drivers for speed trace (max 5):",
        session.laps['Driver'].unique().tolist(),
        default=session.laps['Driver'].unique().tolist()[:3],
        max_selections=5
    )
    
    if trace_drivers:
        fig = create_speed_trace_chart(session, trace_drivers)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            st.info("💡 This shows speed variations around the track for fastest laps")
        else:
            st.warning("Speed trace data not available")

def render_data_export_tab(session):
    """Render data export tab"""
    st.header("Data Export")
    
    # Raw lap data
    st.subheader("Session Data")
    
    lap_data = prepare_export_data(session)
    st.dataframe(lap_data, use_container_width=True)
    
    # Download button
    csv = lap_data.to_csv(index=False)
    st.download_button(
        label="📥 Download Complete Session Data",
        data=csv,
        file_name=f"{st.session_state.event_info.replace(' ', '_')}_complete_data.csv",
        mime='text/csv',
    )

def main():
    """Main application function"""
    # Setup page configuration
    setup_page()
    
    # Render header
    render_header()
    
    # Render sidebar and get selections
    year, event, session_type, events = render_sidebar()
    
    # Check if session is loaded
    if 'session' not in st.session_state:
        render_welcome_screen()
        return
    
    # Get session and stats
    session = st.session_state.session
    stats = get_session_stats(session)
    
    # Render session overview
    render_session_overview(session, stats)
    st.markdown("---")
    
    # Create and render tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Lap Analysis", 
        "⏱️ Sector Times", 
        "📈 Telemetry", 
        "🏁 Position Tracking",
        "🎯 Speed Traces",
        "📋 Data Export"
    ])
    
    with tab1:
        render_lap_analysis_tab(session)
    
    with tab2:
        render_sector_analysis_tab(session)
    
    with tab3:
        render_telemetry_tab(session)
    
    with tab4:
        render_position_tracking_tab(session)
    
    with tab5:
        render_speed_traces_tab(session)
    
    with tab6:
        render_data_export_tab(session)

if __name__ == "__main__":
    main()