"""
F1 Analytics Dashboard - Main Application
Optimized for 2025 ongoing season with enhanced features
"""
import streamlit as st
import pandas as pd

# Import custom modules
from data_loader import (
    get_schedule, load_session, get_session_stats, get_available_years, 
    check_session_availability, get_race_weekend_summary, get_latest_race_data, 
    get_recent_race_highlights, test_2025_data_access
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
        page_title="F1 Analytics Dashboard 2025", 
        page_icon="🏎️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def render_header():
    """Render page header with 2025 season emphasis"""
    st.title("🏎️ Formula 1 Analytics Dashboard")
    
    # Add 2025 season indicator
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown("*Advanced F1 telemetry and race analysis*")
    with col2:
        st.success("🏁 **2025 LIVE SEASON**")
    with col3:
        if st.button("🧪 Test 2025 Data", help="Test 2025 data connectivity"):
            test_2025_data_access()
    
    st.markdown("---")

def render_sidebar():
    """Render sidebar with enhanced 2025 session selection"""
    st.sidebar.header("⚙️ Session Selection")
    
    # Get available years with 2025 priority
    available_years = get_available_years()
    
    if not available_years:
        st.sidebar.error("No F1 data available")
        return None, None, None, None
    
    # Year selection with 2025 as default
    default_year_index = 0 if 2025 in available_years else 0
    year = st.sidebar.selectbox(
        "Season", 
        available_years,
        index=default_year_index,
        help="Select F1 season (2025 = Live ongoing season)"
    )
    
    # Load events with enhanced loading for 2025
    loading_message = "Loading 2025 live schedule..." if year == 2025 else "Loading schedule..."
    with st.spinner(loading_message):
        events = get_schedule(year)
    
    if not events:
        st.sidebar.error(f"No events found for {year}")
        return year, None, None, None
    
    # Enhanced season status display
    current_year = 2025
    if year == current_year:
        st.sidebar.success(f"🏁 {year} Season - LIVE DATA!")
        st.sidebar.info(f"📅 {len(events)} completed race weekends")
        
        # Show next race info
        st.sidebar.markdown("### 🚀 Next Race")
        st.sidebar.info("🇧🇪 **Belgian Grand Prix**\n📅 July 25-27, 2025\n🏁 Spa-Francorchamps")
        
    elif year == 2024:
        st.sidebar.success("🏆 Complete 2024 Season!")
    else:
        st.warning("⚠️ Need at least 2 drivers for telemetry comparison")
        st.info(f"This session has {len(available_drivers)} driver(s). Telemetry comparison requires 2 or more drivers.")

def render_position_tracking_tab(session):
    """Enhanced position tracking tab"""
    st.header("🏁 Race Position Tracking")
    
    current_year = st.session_state.get('year', 2024)
    if current_year == 2025:
        st.markdown("*Tracking 2025 race positions*")
    
    if session.session_info['Type'] == 'R':
        with st.spinner("Analyzing position changes throughout the race..."):
            result = create_position_tracking_chart(session)
        
        if result[0]:
            fig, changes_df = result
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📊 Position Changes Analysis")
            
            # Enhanced position changes display
            if not changes_df.empty:
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
                
                # Full changes table
                st.subheader("📋 Complete Position Changes")
                st.dataframe(changes_df, use_container_width=True)
                
                # Add 2025 insights
                if current_year == 2025:
                    try:
                        best_gainer = changes_df.loc[changes_df['Positions Gained'].idxmax()]
                        if best_gainer['Positions Gained'] > 0:
                            st.success(f"🏆 **2025 Race Hero**: {best_gainer['Driver']} gained {best_gainer['Positions Gained']} positions!")
                    except:
                        pass
            else:
                st.info("No position change data available")
        else:
            st.warning("⚠️ Position tracking data not available")
            st.info("💡 Position data is typically available for completed races")
    else:
        st.info("📋 Position tracking is only available for race sessions")
        st.markdown("Select a **Race (R)** session to view position changes throughout the race.")

def render_speed_traces_tab(session):
    """Enhanced speed traces tab"""
    st.header("🎯 Speed Trace Analysis")
    
    current_year = st.session_state.get('year', 2024)
    if current_year == 2025:
        st.markdown("*Analyzing 2025 speed patterns around the track*")
    
    available_drivers = session.laps['Driver'].unique().tolist()
    
    # Enhanced driver selection
    trace_drivers = st.multiselect(
        "Select drivers for speed trace analysis (max 5):",
        available_drivers,
        default=available_drivers[:min(3, len(available_drivers))],
        max_selections=5,
        help="Choose drivers to compare speed variations around the track"
    )
    
    if trace_drivers:
        with st.spinner(f"Generating speed traces for {len(trace_drivers)} drivers..."):
            fig = create_speed_trace_chart(session, trace_drivers)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            # Enhanced speed trace insights
            st.subheader("🔍 Speed Analysis Insights")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("💡 **Speed Traces**: Shows speed variations around the track for fastest laps")
                st.markdown("- **High speed sections**: Straights and fast corners")
                st.markdown("- **Low speed sections**: Tight corners and chicanes")
            
            with col2:
                st.info("🏁 **Track Analysis**: Compare driver approaches")
                st.markdown("- **Braking points**: Where speed drops rapidly")
                st.markdown("- **Acceleration zones**: Where speed increases")
            
            # Add 2025 specific insights
            if current_year == 2025:
                st.success("🏁 **2025 Live Data**: Real-time speed analysis from the current season!")
        else:
            st.warning("⚠️ Speed trace data not available for selected drivers")
            st.info("💡 Speed traces require telemetry data, typically available for recent sessions")
    else:
        st.warning("Please select at least one driver to analyze speed traces")

def render_data_export_tab(session):
    """Enhanced data export tab"""
    st.header("📋 Data Export & Download")
    
    current_year = st.session_state.get('year', 2024)
    if current_year == 2025:
        st.markdown("*Export live 2025 F1 data*")
    
    # Enhanced session data display
    st.subheader("📊 Session Data Overview")
    
    # Show session summary
    try:
        total_laps = len(session.laps)
        total_drivers = len(session.laps['Driver'].unique())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔄 Total Laps", total_laps)
        with col2:
            st.metric("🏎️ Drivers", total_drivers)
        with col3:
            data_size = f"{total_laps * total_drivers} data points"
            st.metric("📈 Data Points", data_size)
    except:
        st.info("Session data loading...")
    
    # Enhanced data preview
    st.subheader("📋 Data Preview")
    
    lap_data = prepare_export_data(session)
    
    if lap_data is not None and not lap_data.empty:
        # Show sample data
        st.markdown("**Sample data (first 10 rows):**")
        st.dataframe(lap_data.head(10), use_container_width=True)
        
        # Enhanced download options
        st.subheader("📥 Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Full data download
            csv_full = lap_data.to_csv(index=False)
            filename_full = f"{st.session_state.event_info.replace(' ', '_')}_complete_data.csv"
            
            st.download_button(
                label="📥 Download Complete Dataset",
                data=csv_full,
                file_name=filename_full,
                mime='text/csv',
                help="Download all session data as CSV",
                use_container_width=True
            )
        
        with col2:
            # Summary data download
            if len(lap_data) > 100:
                # Create summary for large datasets
                try:
                    summary_data = lap_data.groupby('Driver').agg({
                        'LapTime': ['count', 'min', 'mean'],
                        'Position': 'last'
                    }).round(3)
                    
                    csv_summary = summary_data.to_csv()
                    filename_summary = f"{st.session_state.event_info.replace(' ', '_')}_summary.csv"
                    
                    st.download_button(
                        label="📊 Download Summary Data",
                        data=csv_summary,
                        file_name=filename_summary,
                        mime='text/csv',
                        help="Download summarized driver statistics",
                        use_container_width=True
                    )
                except:
                    st.info("Summary data not available")
        
        # Data statistics
        st.subheader("📈 Data Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Rows", len(lap_data))
        with col2:
            st.metric("📋 Columns", len(lap_data.columns))
        with col3:
            file_size = len(csv_full.encode('utf-8')) / 1024  # KB
            st.metric("💾 File Size", f"{file_size:.1f} KB")
        
        # Show column information
        with st.expander("📋 Column Descriptions"):
            st.markdown("""
            **Available Data Columns:**
            - **Driver**: Driver name/code
            - **LapNumber**: Lap number in session
            - **LapTime**: Total lap time
            - **Sector1Time, Sector2Time, Sector3Time**: Individual sector times
            - **Position**: Track position during lap
            - **SpeedI1, SpeedI2, SpeedFL, SpeedST**: Speed measurements at different track points
            """)
        
        # Add 2025 data note
        if current_year == 2025:
            st.success("🏁 **2025 Live Data**: You're downloading real-time F1 season data!")
    
    else:
        st.error("❌ No data available for export")
        st.info("💡 Try loading a different session or check your data connection")

def main():
    """Enhanced main application function with 2025 optimizations"""
    # Setup page configuration
    setup_page()
    
    # Render enhanced header
    render_header()
    
    # Render enhanced sidebar and get selections
    year, event, session_type, events = render_sidebar()
    
    # Check if session is loaded
    if 'session' not in st.session_state:
        render_welcome_screen()
        return
    
    # Get session and stats
    session = st.session_state.session
    stats = get_session_stats(session)
    
    # Render enhanced session overview
    render_session_overview(session, stats)
    st.markdown("---")
    
    # Create and render enhanced tabs
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
        st.sidebar.info(f"📚 {year} Historical Data")
    
    # Event selection with enhanced info for 2025
    if year == 2025:
        # Add helpful descriptions for 2025 events
        event_descriptions = {
            "British Grand Prix": "🏁 Latest completed race (July 4-6)",
            "Austrian Grand Prix": "🏔️ Recent race at Red Bull Ring",
            "Canadian Grand Prix": "🍁 Montreal street circuit",
            "Monaco Grand Prix": "🏰 Monaco street circuit classic",
            "Australian Grand Prix": "🇦🇺 2025 season opener"
        }
        
        # Show most recent races first for 2025
        events_display = events.copy()
        
        selected_event_index = st.sidebar.selectbox(
            "Race Event", 
            range(len(events_display)),
            format_func=lambda i: f"{events_display[i]} {event_descriptions.get(events_display[i], '')}"
        )
        event = events_display[selected_event_index]
    else:
        event = st.sidebar.selectbox("Race Event", events)
    
    # Check available sessions for selected event
    if event:
        available_sessions = check_session_availability(year, event)
        weekend_summary = get_race_weekend_summary(year, event)
        
        # Enhanced race weekend status for 2025
        if year == 2025:
            if weekend_summary['status'] == 'completed':
                st.sidebar.success("✅ Race Weekend Complete")
            elif weekend_summary['status'] == 'qualifying_done':
                st.sidebar.info("🏁 Qualifying Done, Race Pending")
            elif weekend_summary['status'] == 'practice_only':
                st.sidebar.warning("⚠️ Practice Sessions Only")
            elif weekend_summary['status'] == 'upcoming':
                st.sidebar.info("📅 Upcoming Race Weekend")
            else:
                st.sidebar.error("❌ No Data Available")
        else:
            # Standard status for historical years
            if weekend_summary['status'] == 'completed':
                st.sidebar.success("✅ Race Weekend Complete")
            elif weekend_summary['status'] == 'qualifying_done':
                st.sidebar.info("🏁 Qualifying Done, Race Pending")
            elif weekend_summary['status'] == 'practice_only':
                st.sidebar.warning("⚠️ Practice Sessions Only")
            else:
                st.sidebar.error("❌ No Data Available")
        
        # Show available sessions with enhanced display
        if available_sessions:
            session_names = {
                'R': '🏁 Race', 'Q': '🏁 Qualifying', 'S': '🏃 Sprint',
                'FP1': '🔧 Free Practice 1', 'FP2': '🔧 Free Practice 2', 'FP3': '🔧 Free Practice 3'
            }
            available_session_names = [session_names.get(s, s) for s in available_sessions]
            st.sidebar.success(f"📊 Available: {', '.join(available_session_names)}")
        
        # Session selection - prioritize available sessions
        if available_sessions:
            session_options = available_sessions
            session_help = "Showing only available sessions with data"
        else:
            session_options = ["R", "Q", "FP3", "FP2", "FP1", "S"]
            session_help = "Some sessions may not have data yet"
        
        # Enhanced session selector with descriptions
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
            help=session_help
        )
    else:
        session_type = st.sidebar.selectbox(
            "Session", 
            ["R", "Q", "FP3", "FP2", "FP1", "S"],
            help="Select session type"
        )
    
    # Enhanced load button with 2025 optimizations
    load_button_text = "🔄 Load Live 2025 Data" if year == 2025 else "🔄 Load Session Data"
    
    if st.sidebar.button(load_button_text, type="primary", use_container_width=True):
        # Enhanced loading with progress for 2025
        if year == 2025:
            with st.spinner(f"Loading live 2025 data: {event} {session_type}..."):
                session = load_session(year, event, session_type)
        else:
            with st.spinner("Loading session data..."):
                session = load_session(year, event, session_type)
        
        if session:
            st.session_state.session = session
            st.session_state.event_info = f"{event} {session_type} ({year})"
            st.session_state.year = year
            st.sidebar.success("✅ Data loaded successfully!")
            
            # Show additional info for 2025 season
            if year == 2025:
                st.sidebar.success("🏁 Live 2025 season data loaded!")
                # Show data freshness
                if hasattr(session, 'date') and session.date:
                    from datetime import datetime
                    days_ago = (datetime.now().date() - session.date).days
                    if days_ago == 0:
                        st.sidebar.info("📊 Data from today!")
                    elif days_ago == 1:
                        st.sidebar.info("📊 Data from yesterday")
                    else:
                        st.sidebar.info(f"📊 Data from {days_ago} days ago")
        else:
            st.sidebar.error("❌ Failed to load data")
            if year == 2025:
                if session_type not in (available_sessions if 'available_sessions' in locals() else []):
                    st.sidebar.warning("💡 This 2025 session may not have occurred yet")
                else:
            st.sidebar.info("💡 Try a different session type or check your connection")
        
        # Show current session info with enhanced 2025 display
        if 'session' in st.session_state:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 📊 Current Session")
            
            # Enhanced session info display
            session_info = st.session_state.event_info
            if st.session_state.get('year') == 2025:
                st.sidebar.success(f"🏁 **{session_info}** (LIVE)")
            else:
                st.sidebar.info(f"📊 {session_info}")
            
            # Show session insights
            session = st.session_state.session
            if hasattr(session, 'date') and session.date:
                st.sidebar.text(f"📅 {session.date}")
                
            # Show quick stats
            try:
                lap_count = len(session.laps)
                driver_count = len(session.laps['Driver'].unique()) if hasattr(session, 'laps') else 0
                st.sidebar.text(f"🏎️ {driver_count} drivers")
                st.sidebar.text(f"🔄 {lap_count} laps")
            except:
                pass
    
    def render_position_tracking_tab(session):
    
    return year, event, session_type, events

def render_welcome_screen():
    """Enhanced welcome screen with 2025 focus"""
    st.markdown("## 🏎️ F1 2025 Live Season Analysis")
    
    # Get latest race data with 2025 priority
    latest_race = get_latest_race_data()
    
    if latest_race:
        session = latest_race['session']
        stats = get_session_stats(session)
        
        # Enhanced latest race header for 2025
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            race_title = f"🏁 **{latest_race['event']} {latest_race['year']}**"
            if latest_race['year'] == 2025:
                race_title += " *(LIVE SEASON)*"
            st.markdown(f"### {race_title}")
            
            if latest_race['status'] == 'race_complete':
                st.success("✅ Race Complete")
            else:
                st.info("🏁 Latest Qualifying")
        
        with col2:
            st.metric("📅 Date", stats.get('session_date', 'Unknown'))
        
        with col3:
            session_display = latest_race['session_type']
            if latest_race['year'] == 2025:
                session_display += " (2025)"
            st.metric("🏎️ Session", session_display)
        
        # Enhanced quick stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            fastest_driver = stats.get('fastest_lap_driver', 'N/A')
            st.metric("🏆 Fastest Driver", fastest_driver)
        with col2:
            fastest_time = stats.get('fastest_lap_time', 'N/A')
            st.metric("⚡ Fastest Lap", fastest_time)
        with col3:
            st.metric("👥 Drivers", stats.get('total_drivers', 0))
        with col4:
            st.metric("🔄 Total Laps", stats.get('total_laps', 0))
        
        # Enhanced auto-load button for 2025
        button_text = "🔄 Analyze This 2025 Race" if latest_race['year'] == 2025 else "🔄 Analyze This Race"
        if st.button(button_text, type="primary", use_container_width=True):
            st.session_state.session = session
            st.session_state.event_info = f"{latest_race['event']} {latest_race['session_type']} ({latest_race['year']})"
            st.session_state.year = latest_race['year']
            st.rerun()
        
        # Enhanced race analysis for 2025
        if latest_race['session_type'] == 'R':
            st.markdown("### 📊 2025 Race Analysis" if latest_race['year'] == 2025 else "### 📊 Race Analysis")
            
            # Get top 5 drivers by final position
            try:
                final_positions = session.laps.groupby('Driver')['Position'].last().dropna()
                top_drivers = final_positions.sort_values().head(5).index.tolist()
                
                fig = create_lap_times_chart(session, top_drivers)
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Enhanced podium display for 2025
                podium = final_positions.sort_values().head(3)
                podium_title = "### 🏆 2025 Podium" if latest_race['year'] == 2025 else "### 🏆 Podium"
                st.markdown(podium_title)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    winner = podium.index[0] if len(podium) > 0 else 'N/A'
                    st.markdown(f"**🥇 1st:** {winner}")
                with col2:
                    second = podium.index[1] if len(podium) > 1 else 'N/A'
                    st.markdown(f"**🥈 2nd:** {second}")
                with col3:
                    third = podium.index[2] if len(podium) > 2 else 'N/A'
                    st.markdown(f"**🥉 3rd:** {third}")
                
            except Exception as e:
                st.info("Race analysis loading...")
        
        elif latest_race['session_type'] == 'Q':
            quali_title = "### 🏁 2025 Qualifying Results" if latest_race['year'] == 2025 else "### 🏁 Qualifying Results"
            st.markdown(quali_title)
            
            # Enhanced qualifying results
            try:
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
                    
                    # Enhanced top 3 display
                    top3_title = "### 🏆 Top 3 2025 Qualifiers" if latest_race['year'] == 2025 else "### 🏆 Top 3 Qualifiers"
                    st.markdown(top3_title)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        pole_driver = df.iloc[0]['Driver']
                        pole_time = df.iloc[0]['Lap Time']
                        st.markdown(f"**🥇 Pole:** {pole_driver}")
                        st.markdown(f"*{pole_time}*")
                    with col2:
                        if len(df) > 1:
                            second_driver = df.iloc[1]['Driver']
                            second_time = df.iloc[1]['Lap Time']
                            st.markdown(f"**🥈 2nd:** {second_driver}")
                            st.markdown(f"*{second_time}*")
                        else:
                            st.markdown("**🥈 2nd:** N/A")
                    with col3:
                        if len(df) > 2:
                            third_driver = df.iloc[2]['Driver']
                            third_time = df.iloc[2]['Lap Time']
                            st.markdown(f"**🥉 3rd:** {third_driver}")
                            st.markdown(f"*{third_time}*")
                        else:
                            st.markdown("**🥉 3rd:** N/A")
                    
                    # Show full results table
                    results_title = "### 📋 Full 2025 Qualifying Results" if latest_race['year'] == 2025 else "### 📋 Full Qualifying Results"
                    st.markdown(results_title)
                    display_df = df[['Position', 'Driver', 'Lap Time']].reset_index(drop=True)
                    st.dataframe(display_df, use_container_width=True)
                
            except Exception as e:
                st.info("Qualifying analysis loading...")
    
    else:
        st.info("⏳ Loading latest 2025 race data...")
        
        # Show manual selection as fallback
        st.markdown("### 🔧 Manual Selection")
        st.markdown("Use the sidebar to manually select a 2025 race for analysis")
    
    # Enhanced recent race highlights with 2025 focus
    st.markdown("---")
    st.markdown("### 📰 Recent F1 Highlights")
    
    highlights = get_recent_race_highlights()
    if highlights:
        for highlight in highlights:
            # Enhanced highlight display for 2025
            year_badge = "🏁 LIVE 2025" if highlight['year'] == 2025 else f"📚 {highlight['year']}"
            
            with st.expander(f"{year_badge} - {highlight['event']} ({highlight['session_date']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**🏆 Winner:** {highlight['winner']}")
                    st.markdown(f"**⚡ Fastest Lap:** {highlight['fastest_lap_driver']} ({highlight['fastest_lap_time']})")
                with col2:
                    st.markdown("**🏆 Podium:**")
                    for i, driver in enumerate(highlight['podium'][:3]):
                        medals = ['🥇', '🥈', '🥉']
                        st.markdown(f"{medals[i]} {driver}")
    
    # Enhanced getting started section
    st.markdown("---")
    st.markdown("### 🚀 F1 2025 Advanced Analytics")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📊 2025 Live Analysis:**")
        st.markdown("- Real-time lap performance tracking")
        st.markdown("- Position changes throughout races")
        st.markdown("- Live tire strategy analysis")
        st.markdown("- Pit stop timing and impact")
    
    with col2:
        st.markdown("**🔧 Technical Deep Dive:**")
        st.markdown("- Sector time micro-analysis")
        st.markdown("- Speed traces by track distance")
        st.markdown("- Telemetry data (throttle, brake, gear)")
        st.markdown("- Driver performance comparisons")
    
    # Enhanced quick start message
    if latest_race and latest_race['year'] == 2025:
        st.success("🏁 **2025 Live Season**: Click 'Analyze This 2025 Race' above for instant analysis of the latest race!")
    else:
        st.info("💡 **Quick Start**: Use the sidebar to explore 2025 races or analyze historical data!")

def render_session_overview(session, stats):
    """Enhanced session overview with 2025 features"""
    # Enhanced metrics display
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔄 Total Laps", stats.get('total_laps', 0))
    with col2:
        st.metric("🏎️ Drivers", stats.get('total_drivers', 0))
    with col3:
        fastest_time = stats.get('fastest_lap_time', 'N/A')
        st.metric("⚡ Fastest Lap", fastest_time)
    with col4:
        fastest_driver = stats.get('fastest_lap_driver', 'N/A')
        st.metric("🏆 Fastest Driver", fastest_driver)
    
    # Enhanced session info
    info_text = format_session_info(stats)
    if info_text:
        st.markdown(info_text)
    
    # Enhanced season indicator with 2025 emphasis
    current_year = st.session_state.get('year', 2024)
    indicator_text, indicator_type = get_season_indicator(current_year)
    
    if current_year == 2025:
        st.success(f"🏁 {indicator_text}")
        # Add live season stats
        try:
            session_date = stats.get('session_date', '')
            if session_date:
                from datetime import datetime
                session_dt = datetime.strptime(session_date, "%Y-%m-%d").date()
                days_ago = (datetime.now().date() - session_dt).days
                if days_ago <= 7:
                    st.info(f"📊 Fresh data from {days_ago} days ago!")
        except:
            pass
    elif indicator_type == "success":
        st.success(indicator_text)
    else:
        st.info(indicator_text)

def render_lap_analysis_tab(session):
    """Enhanced lap analysis tab"""
    st.header("📊 Lap Time Analysis")
    
    all_drivers = session.laps['Driver'].unique().tolist()
    
    # Enhanced driver selection for 2025
    current_year = st.session_state.get('year', 2024)
    if current_year == 2025:
        st.markdown("*Analyzing live 2025 season data*")
    
    # Smart default selection
    default_count = min(5, len(all_drivers))
    selected_drivers = st.multiselect(
        "Select drivers for analysis (max 10):", 
        all_drivers, 
        default=all_drivers[:default_count],
        max_selections=10,
        help="Choose drivers to compare lap times throughout the session"
    )
    
    if selected_drivers:
        # Enhanced chart with loading indicator
        with st.spinner("Creating lap time analysis..."):
            fig = create_lap_times_chart(session, selected_drivers)
            st.plotly_chart(fig, use_container_width=True)
        
        # Enhanced lap statistics table
        st.subheader("📈 Detailed Lap Statistics")
        lap_stats_df = calculate_lap_statistics(session, selected_drivers)
        
        if lap_stats_df is not None:
            st.dataframe(lap_stats_df, use_container_width=True)
            
            # Add insights for 2025
            if current_year == 2025:
                try:
                    best_driver = lap_stats_df.loc[lap_stats_df['Best Lap'].str.replace('s', '').astype(float).idxmin(), 'Driver']
                    st.info(f"💡 **2025 Session Leader**: {best_driver} set the fastest lap time")
                except:
                    pass
    else:
        st.warning("Please select at least one driver to analyze lap times")

def render_sector_analysis_tab(session):
    """Enhanced sector analysis tab"""
    st.header("⏱️ Sector Time Analysis")
    
    current_year = st.session_state.get('year', 2024)
    if current_year == 2025:
        st.markdown("*Analyzing 2025 sector performance*")
    
    with st.spinner("Analyzing sector times..."):
        result = create_sector_analysis_chart(session)
    
    if result[0]:
        fig, df = result
        st.plotly_chart(fig, use_container_width=True)
        
        # Enhanced sector analysis insights
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
        
        st.subheader("📊 Complete Sector Analysis")
        
        # Enhanced dataframe display
        df_display = df.round(3)
        st.dataframe(df_display, use_container_width=True)
        
        # Add 2025 insights
        if current_year == 2025:
            try:
                best_overall = df.loc[df['Total'].idxmin(), 'Driver']
                st.success(f"🏁 **2025 Overall Fastest**: {best_overall} had the best combined sector times")
            except:
                pass
    else:
        st.warning("⚠️ No sector time data available for this session")
        st.info("💡 Try a different session type - sector data is typically available in Qualifying and Practice sessions")

def render_telemetry_tab(session):
    """Enhanced telemetry analysis tab"""
    st.header("📈 Advanced Telemetry Analysis")
    
    current_year = st.session_state.get('year', 2024)
    if current_year == 2025:
        st.markdown("*Analyzing 2025 telemetry data*")
    
    available_drivers = session.laps['Driver'].unique().tolist()
    
    if len(available_drivers) >= 2:
        col1, col2 = st.columns(2)
        with col1:
            driver1 = st.selectbox("Primary Driver", available_drivers, key="tel_driver1")
        with col2:
            available_drivers_2 = [d for d in available_drivers if d != driver1]
            driver2 = st.selectbox("Comparison Driver", available_drivers_2, key="tel_driver2")
        
        if driver1 != driver2:
            with st.spinner(f"Loading telemetry data for {driver1} vs {driver2}..."):
                fig = create_telemetry_chart(session, driver1, driver2)
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                # Enhanced telemetry insights
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
                    
                    # Add comparison insights
                    try:
                        speed_diff = insights[driver1]['max_speed'] - insights[driver2]['max_speed']
                        if abs(speed_diff) > 1:
                            faster_driver = driver1 if speed_diff > 0 else driver2
                            st.info(f"🏁 **Speed Advantage**: {faster_driver} had {abs(speed_diff):.1f} km/h higher max speed")
                    except:
                        pass
            else:
                st.warning("⚠️ Telemetry data not available for selected drivers")
                st.info("💡 Telemetry is typically available for recent races and qualifying sessions")
        else:
            st.warning("Please select two different drivers for comparison")
    else:
        st.warning("⚠️ Need at least 2 drivers for telemetry comparison")
        st.info(f"This session has {len(available_drivers)} driver(s). Telemetry comparison requires 2 or more drivers.")