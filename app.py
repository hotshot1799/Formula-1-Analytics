"""
F1 Analytics Dashboard - Complete Application
Works with 2024/2025 data with automatic fallback
"""
import streamlit as st
import pandas as pd

# Import custom modules
from data_loader import (
    get_schedule, load_session, get_session_stats, get_available_years, 
    check_session_availability, get_race_weekend_summary, get_latest_race_data, 
    get_recent_race_highlights
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
    """Render page header with season status"""
    st.title("🏎️ Formula 1 Analytics Dashboard")
    
    # Dynamic season indicator
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("*Advanced F1 telemetry and race analysis*")
    with col2:
        current_year = 2025
        available_years = get_available_years()
        if current_year in available_years:
            st.success(f"🏁 **{current_year} LIVE SEASON**")
        else:
            st.info(f"📚 **{max(available_years)} SEASON**")
    with col3:
        if st.button("🔄 Refresh Data", help="Refresh data connection"):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")

def render_sidebar():
    """Render sidebar with session selection"""
    st.sidebar.header("⚙️ Session Selection")
    
    # Get available years
    available_years = get_available_years()
    
    if not available_years:
        st.sidebar.error("No F1 data available - check your connection")
        return None, None, None, None
    
    # Year selection with smart default
    default_year = available_years[0]  # Most recent available year
    year = st.sidebar.selectbox(
        "Season", 
        available_years,
        help=f"Select F1 season (Latest: {default_year})"
    )
    
    # Load events with loading indicator
    loading_message = f"Loading {year} schedule..."
    with st.spinner(loading_message):
        events = get_schedule(year)
    
    if not events:
        st.sidebar.error(f"No events found for {year}")
        return year, None, None, None
    
    # Season status display
    current_year = 2025
    if year == current_year:
        st.sidebar.success(f"🏁 {year} Season - LIVE!")
        st.sidebar.info(f"📅 {len(events)} race weekends available")
    elif year == 2024:
        st.sidebar.success("🏆 Complete 2024 Season")
    else:
        st.sidebar.info(f"📚 {year} Historical Data")
    
    # Event selection with enhanced display
    if len(events) > 10:
        # For seasons with many events, show recent ones first
        events_display = events[-10:] + events[:-10]  # Recent 10 first
        event = st.sidebar.selectbox(
            "Race Event", 
            events_display,
            help="Showing recent events first"
        )
    else:
        event = st.sidebar.selectbox("Race Event", events)
    
    # Check available sessions
    if event:
        available_sessions = check_session_availability(year, event)
        weekend_summary = get_race_weekend_summary(year, event)
        
        # Weekend status display
        status_colors = {
            'completed': 'success',
            'qualifying_done': 'info', 
            'practice_only': 'warning',
            'upcoming': 'info',
            'no_data': 'error'
        }
        
        status_messages = {
            'completed': "✅ Race Weekend Complete",
            'qualifying_done': "🏁 Qualifying Done",
            'practice_only': "⚠️ Practice Sessions Only", 
            'upcoming': "📅 Upcoming Race Weekend",
            'no_data': "❌ No Data Available"
        }
        
        status = weekend_summary.get('status', 'unknown')
        if status in status_messages:
            if status_colors[status] == 'success':
                st.sidebar.success(status_messages[status])
            elif status_colors[status] == 'info':
                st.sidebar.info(status_messages[status])
            elif status_colors[status] == 'warning':
                st.sidebar.warning(status_messages[status])
            else:
                st.sidebar.error(status_messages[status])
        
        # Available sessions display
        if available_sessions:
            session_names = {
                'R': '🏁 Race', 'Q': '🏁 Qualifying', 'S': '🏃 Sprint',
                'FP1': '🔧 Free Practice 1', 'FP2': '🔧 Free Practice 2', 'FP3': '🔧 Free Practice 3'
            }
            session_list = [session_names.get(s, s) for s in available_sessions]
            st.sidebar.success(f"📊 Available: {', '.join(session_list)}")
            session_options = available_sessions
        else:
            session_options = ["R", "Q", "FP3", "FP2", "FP1", "S"]
            st.sidebar.info("⏳ Checking session availability...")
        
        # Session selection
        session_descriptions = {
            'R': 'Race - Main event',
            'Q': 'Qualifying - Grid positions', 
            'S': 'Sprint - Short race',
            'FP3': 'Free Practice 3 - Final practice',
            'FP2': 'Free Practice 2 - Long runs',
            'FP1': 'Free Practice 1 - Initial setup'
        }
        
        session_type = st.sidebar.selectbox(
            "Session",
            session_options,
            format_func=lambda x: f"{x} - {session_descriptions.get(x, 'Session')}",
            help="Select session type for analysis"
        )
    else:
        session_type = "R"
    
    # Load button
    load_button_text = f"🔄 Load {year} Session Data"
    
    if st.sidebar.button(load_button_text, type="primary", use_container_width=True):
        with st.spinner(f"Loading {event} {session_type} ({year})..."):
            session = load_session(year, event, session_type)
        
        if session:
            st.session_state.session = session
            st.session_state.event_info = f"{event} {session_type} ({year})"
            st.session_state.year = year
            st.sidebar.success("✅ Data loaded successfully!")
            
            # Show data quality info
            if hasattr(session, 'laps') and not session.laps.empty:
                lap_count = len(session.laps)
                driver_count = len(session.laps['Driver'].unique())
                st.sidebar.info(f"📊 {driver_count} drivers, {lap_count} laps")
        else:
            st.sidebar.error("❌ Failed to load session data")
            if session_type not in available_sessions:
                st.sidebar.warning("💡 This session may not be available")
            else:
                st.sidebar.info("💡 Try a different session or check connection")
    
    # Current session display
    if 'session' in st.session_state:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Current Session")
        
        session_info = st.session_state.event_info
        session_year = st.session_state.get('year', 2024)
        
        if session_year == 2025:
            st.sidebar.success(f"🏁 **{session_info}** (LIVE)")
        else:
            st.sidebar.info(f"📊 {session_info}")
        
        # Session details
        try:
            session = st.session_state.session
            if hasattr(session, 'date') and session.date:
                st.sidebar.text(f"📅 {session.date}")
            
            if hasattr(session, 'laps'):
                lap_count = len(session.laps)
                driver_count = len(session.laps['Driver'].unique())
                st.sidebar.text(f"🏎️ {driver_count} drivers")
                st.sidebar.text(f"🔄 {lap_count} laps")
        except:
            pass
    
    return year, event, session_type, events

def render_welcome_screen():
    """Welcome screen with latest race analysis"""
    st.markdown("## 🏎️ Latest F1 Race Analysis")
    
    # Get latest race data
    latest_race = get_latest_race_data()
    
    if latest_race:
        session = latest_race['session']
        stats = get_session_stats(session)
        
        # Latest race header
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            race_title = f"🏁 **{latest_race['event']} {latest_race['year']}**"
            if latest_race['year'] >= 2024:
                race_title += " *(Latest Season)*"
            st.markdown(f"### {race_title}")
            
            if latest_race['status'] == 'race_complete':
                st.success("✅ Race Complete")
            else:
                st.info("🏁 Latest Qualifying")
        
        with col2:
            st.metric("📅 Date", stats.get('session_date', 'Unknown'))
        
        with col3:
            st.metric("🏎️ Session", latest_race['session_type'])
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏆 Fastest Driver", stats.get('fastest_lap_driver', 'N/A'))
        with col2:
            st.metric("⚡ Fastest Lap", stats.get('fastest_lap_time', 'N/A'))
        with col3:
            st.metric("👥 Drivers", stats.get('total_drivers', 0))
        with col4:
            st.metric("🔄 Total Laps", stats.get('total_laps', 0))
        
        # Auto-load button
        if st.button("🔄 Analyze This Race", type="primary", use_container_width=True):
            st.session_state.session = session
            st.session_state.event_info = f"{latest_race['event']} {latest_race['session_type']} ({latest_race['year']})"
            st.session_state.year = latest_race['year']
            st.rerun()
        
        # Race analysis
        if latest_race['session_type'] == 'R':
            st.markdown("### 📊 Quick Race Analysis")
            
            try:
                # Get top 5 drivers by final position
                final_positions = session.laps.groupby('Driver')['Position'].last().dropna()
                top_drivers = final_positions.sort_values().head(5).index.tolist()
                
                if top_drivers:
                    fig = create_lap_times_chart(session, top_drivers)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Podium
                    podium = final_positions.sort_values().head(3)
                    st.markdown("### 🏆 Podium")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**🥇 1st:** {podium.index[0] if len(podium) > 0 else 'N/A'}")
                    with col2:
                        st.markdown(f"**🥈 2nd:** {podium.index[1] if len(podium) > 1 else 'N/A'}")
                    with col3:
                        st.markdown(f"**🥉 3rd:** {podium.index[2] if len(podium) > 2 else 'N/A'}")
                
            except Exception as e:
                st.info("Race analysis loading...")
        
        elif latest_race['session_type'] == 'Q':
            st.markdown("### 🏁 Qualifying Results")
            
            try:
                # Get qualifying results
                fastest_laps = []
                for driver in session.laps['Driver'].unique():
                    try:
                        fastest_lap = session.laps.pick_driver(driver).pick_fastest()
                        fastest_laps.append({
                            'Driver': driver,
                            'Fastest Lap': fastest_lap['LapTime'].total_seconds(),
                            'Lap Time': str(fastest_lap['LapTime'])
                        })
                    except:
                        continue
                
                if fastest_laps:
                    df = pd.DataFrame(fastest_laps)
                    df = df.sort_values('Fastest Lap').head(10)
                    df['Position'] = range(1, len(df) + 1)
                    
                    # Top 3
                    st.markdown("### 🏆 Top 3 Qualifiers")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if len(df) > 0:
                            st.markdown(f"**🥇 Pole:** {df.iloc[0]['Driver']}")
                            st.markdown(f"*{df.iloc[0]['Lap Time']}*")
                    with col2:
                        if len(df) > 1:
                            st.markdown(f"**🥈 2nd:** {df.iloc[1]['Driver']}")
                            st.markdown(f"*{df.iloc[1]['Lap Time']}*")
                    with col3:
                        if len(df) > 2:
                            st.markdown(f"**🥉 3rd:** {df.iloc[2]['Driver']}")
                            st.markdown(f"*{df.iloc[2]['Lap Time']}*")
                    
                    # Full results
                    st.markdown("### 📋 Full Qualifying Results")
                    display_df = df[['Position', 'Driver', 'Lap Time']].reset_index(drop=True)
                    st.dataframe(display_df, use_container_width=True)
                
            except Exception as e:
                st.info("Qualifying analysis loading...")
    
    else:
        st.info("⏳ Loading latest race data...")
        st.markdown("### 🔧 Manual Selection")
        st.markdown("Use the sidebar to select a race for analysis")
    
    # Recent race highlights
    st.markdown("---")
    st.markdown("### 📰 Recent Race Highlights")
    
    highlights = get_recent_race_highlights()
    if highlights:
        for highlight in highlights:
            year_badge = f"🏁 {highlight['year']}" if highlight['year'] >= 2024 else f"📚 {highlight['year']}"
            
            with st.expander(f"{year_badge} - {highlight['event']} ({highlight['session_date']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**🏆 Winner:** {highlight['winner']}")
                    st.markdown(f"**⚡ Fastest Lap:** {highlight['fastest_lap_driver']} ({highlight['fastest_lap_time']})")
                with col2:
                    st.markdown("**🏆 Podium:**")
                    medals = ['🥇', '🥈', '🥉']
                    for i, driver in enumerate(highlight['podium'][:3]):
                        st.markdown(f"{medals[i]} {driver}")
    
    # Features overview
    st.markdown("---")
    st.markdown("### 🚀 Advanced Analytics Available")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📊 Race Analysis:**")
        st.markdown("- Lap-by-lap performance tracking")
        st.markdown("- Position changes throughout race")
        st.markdown("- Tire strategy analysis")
        st.markdown("- Pit stop timing and impact")
    
    with col2:
        st.markdown("**🔧 Technical Analysis:**")
        st.markdown("- Sector time comparisons")
        st.markdown("- Speed traces by track distance")
        st.markdown("- Telemetry (throttle, brake, gear)")
        st.markdown("- Driver performance metrics")
    
    st.info("💡 **Quick Start**: Click 'Analyze This Race' above or use the sidebar to explore different sessions!")

def render_session_overview(session, stats):
    """Render session overview with key metrics"""
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔄 Total Laps", stats.get('total_laps', 0))
    with col2:
        st.metric("🏎️ Drivers", stats.get('total_drivers', 0))
    with col3:
        st.metric("⚡ Fastest Lap", stats.get('fastest_lap_time', 'N/A'))
    with col4:
        st.metric("🏆 Fastest Driver", stats.get('fastest_lap_driver', 'N/A'))
    
    # Additional session info
    info_text = format_session_info(stats)
    if info_text:
        st.markdown(info_text)
    
    # Season indicator
    current_year = st.session_state.get('year', 2024)
    indicator_text, indicator_type = get_season_indicator(current_year)
    
    if indicator_type == "success":
        st.success(indicator_text)
    else:
        st.info(indicator_text)

def render_lap_analysis_tab(session):
    """Render lap analysis tab"""
    st.header("📊 Lap Time Analysis")
    
    all_drivers = session.laps['Driver'].unique().tolist()
    
    # Driver selection
    default_count = min(5, len(all_drivers))
    selected_drivers = st.multiselect(
        "Select drivers for analysis (max 10):", 
        all_drivers, 
        default=all_drivers[:default_count],
        max_selections=10,
        help="Choose drivers to compare lap times"
    )
    
    if selected_drivers:
        with st.spinner("Creating lap time analysis..."):
            fig = create_lap_times_chart(session, selected_drivers)
            st.plotly_chart(fig, use_container_width=True)
        
        # Lap statistics
        st.subheader("📈 Lap Time Statistics")
        lap_stats_df = calculate_lap_statistics(session, selected_drivers)
        
        if lap_stats_df is not None:
            st.dataframe(lap_stats_df, use_container_width=True)
        else:
            st.warning("No lap statistics available")
    else:
        st.warning("Please select at least one driver to analyze")

def render_sector_analysis_tab(session):
    """Render sector analysis tab"""
    st.header("⏱️ Sector Time Analysis")
    
    with st.spinner("Analyzing sector times..."):
        result = create_sector_analysis_chart(session)
    
    if result[0]:
        fig, df = result
        st.plotly_chart(fig, use_container_width=True)
        
        # Sector champions
        fastest_s1, fastest_s2, fastest_s3 = get_fastest_sector_times(df)
        
        if fastest_s1 is not None:
            st.subheader("🏆 Sector Champions")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🟥 Fastest Sector 1", fastest_s1['Driver'], f"{fastest_s1['Sector1']:.3f}s")
            with col2:
                st.metric("🟨 Fastest Sector 2", fastest_s2['Driver'], f"{fastest_s2['Sector2']:.3f}s")
            with col3:
                st.metric("🟩 Fastest Sector 3", fastest_s3['Driver'], f"{fastest_s3['Sector3']:.3f}s")
        
        st.subheader("📊 Detailed Sector Times")
        st.dataframe(df.round(3), use_container_width=True)
    else:
        st.warning("⚠️ No sector time data available for this session")
        st.info("💡 Sector data is typically available in Qualifying and Practice sessions")

def render_telemetry_tab(session):
    """Render telemetry analysis tab"""
    st.header("📈 Advanced Telemetry Analysis")
    
    available_drivers = session.laps['Driver'].unique().tolist()
    
    if len(available_drivers) >= 2:
        col1, col2 = st.columns(2)
        with col1:
            driver1 = st.selectbox("Primary Driver", available_drivers, key="tel_driver1")
        with col2:
            available_drivers_2 = [d for d in available_drivers if d != driver1]
            driver2 = st.selectbox("Comparison Driver", available_drivers_2, key="tel_driver2")
        
        if driver1 != driver2:
            with st.spinner(f"Loading telemetry for {driver1} vs {driver2}..."):
                fig = create_telemetry_chart(session, driver1, driver2)
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                # Telemetry insights
                st.subheader("🔍 Telemetry Insights")
                insights = get_telemetry_insights(session, driver1, driver2)
                
                if insights:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"### 🏎️ {driver1}")
                        st.metric("🏃 Max Speed", f"{insights[driver1]['max_speed']:.1f} km/h")
                        st.metric("📊 Avg Speed", f"{insights[driver1]['avg_speed']:.1f} km/h")
                        if insights[driver1]['avg_throttle']:
                            st.metric("🔥 Avg Throttle", f"{insights[driver1]['avg_throttle']:.1f}%")
                    
                    with col2:
                        st.markdown(f"### 🏎️ {driver2}")
                        st.metric("🏃 Max Speed", f"{insights[driver2]['max_speed']:.1f} km/h")
                        st.metric("📊 Avg Speed", f"{insights[driver2]['avg_speed']:.1f} km/h")
                        if insights[driver2]['avg_throttle']:
                            st.metric("🔥 Avg Throttle", f"{insights[driver2]['avg_throttle']:.1f}%")
            else:
                st.warning("⚠️ Telemetry data not available for selected drivers")
                st.info("💡 Telemetry is typically available for recent races")
        else:
            st.warning("Please select two different drivers")
    else:
        st.warning("⚠️ Need at least 2 drivers for telemetry comparison")
        st.info(f"This session has {len(available_drivers)} driver(s)")

def render_position_tracking_tab(session):
    """Render position tracking tab"""
    st.header("🏁 Race Position Tracking")
    
    if session.session_info['Type'] == 'R':
        with st.spinner("Analyzing position changes..."):
            result = create_position_tracking_chart(session)
        
        if result[0]:
            fig, changes_df = result
            st.plotly_chart(fig, use_container_width=True)
            
            if not changes_df.empty:
                st.subheader("📊 Position Changes Summary")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 📈 Biggest Gainers")
                    gainers = changes_df[changes_df['Positions Gained'] > 0].head(3)
                    if not gainers.empty:
                        for _, row in gainers.iterrows():
                            st.success(f"🔥 **{row['Driver']}**: +{row['Positions Gained']} positions")
                    else:
                        st.info("No significant position gainers")
                
                with col2:
                    st.markdown("### 📉 Position Losses")
                    losers = changes_df[changes_df['Positions Gained'] < 0].head(3)
                    if not losers.empty:
                        for _, row in losers.iterrows():
                            st.error(f"📉 **{row['Driver']}**: {row['Positions Gained']} positions")
                    else:
                        st.info("No significant position losses")
                
                st.subheader("📋 Complete Position Changes")
                st.dataframe(changes_df, use_container_width=True)
        else:
            st.warning("⚠️ Position data not available")
    else:
        st.info("📋 Position tracking is only available for race sessions")

def render_speed_traces_tab(session):
    """Render speed traces tab"""
    st.header("🎯 Speed Trace Analysis")
    
    available_drivers = session.laps['Driver'].unique().tolist()
    
    trace_drivers = st.multiselect(
        "Select drivers for speed trace (max 5):",
        available_drivers,
        default=available_drivers[:min(3, len(available_drivers))],
        max_selections=5,
        help="Compare speed variations around the track"
    )
    
    if trace_drivers:
        with st.spinner("Generating speed traces..."):
            fig = create_speed_trace_chart(session, trace_drivers)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("💡 **Speed Traces**: Speed variations for fastest laps")
            with col2:
                st.info("🏁 **Analysis**: Compare braking and acceleration points")
        else:
            st.warning("⚠️ Speed trace data not available")
    else:
        st.warning("Please select at least one driver")

def render_data_export_tab(session):
    """Render data export tab"""
    st.header("📋 Data Export")
    
    # Session overview
    st.subheader("📊 Session Data")
    
    try:
        total_laps = len(session.laps)
        total_drivers = len(session.laps['Driver'].unique())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔄 Total Laps", total_laps)
        with col2:
            st.metric("🏎️ Drivers", total_drivers)
        with col3:
            data_points = total_laps * total_drivers
            st.metric("📈 Data Points", data_points)
    except:
        st.info("Loading session data...")
    
    # Data preview and export
    lap_data = prepare_export_data(session)
    
    if lap_data is not None and not lap_data.empty:
        st.subheader("📋 Data Preview")
        st.dataframe(lap_data.head(10), use_container_width=True)
        
        # Download options
        st.subheader("📥 Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = lap_data.to_csv(index=False)
            filename = f"{st.session_state.event_info.replace(' ', '_')}_data.csv"
            
            st.download_button(
                label="📥 Download Complete Dataset",
                data=csv_data,
                file_name=filename,
                mime='text/csv',
                use_container_width=True
            )
        
        with col2:
            # Summary statistics
            try:
                summary_stats = lap_data.groupby('Driver').agg({
                    'LapTime': ['count', 'min', 'mean'],
                    'Position': 'last' if 'Position' in lap_data.columns else 'count'
                }).round(3)
                
                csv_summary = summary_stats.to_csv()
                summary_filename = f"{st.session_state.event_info.replace(' ', '_')}_summary.csv"
                
                st.download_button(
                    label="📊 Download Summary Stats",
                    data=csv_summary,
                    file_name=summary_filename,
                    mime='text/csv',
                    use_container_width=True
                )
            except:
                st.info("Summary not available")
        
        # File info
        file_size = len(csv_data.encode('utf-8')) / 1024
        st.info(f"💾 File size: {file_size:.1f} KB")
    else:
        st.error("❌ No data available for export")

def main():
    """Main application function"""
    # Setup page
    setup_page()
    
    # Render header
    render_header()
    
    # Render sidebar
    year, event, session_type, events = render_sidebar()
    
    # Main content
    if 'session' not in st.session_state:
        render_welcome_screen()
        return
    
    # Session analysis
    session = st.session_state.session
    stats = get_session_stats(session)
    
    # Session overview
    render_session_overview(session, stats)
    st.markdown("---")
    
    # Analysis tabs
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