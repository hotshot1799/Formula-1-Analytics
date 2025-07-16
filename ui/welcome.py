"""
Welcome screen component
"""
import streamlit as st
import pandas as pd
from data_loader import get_latest_race_data, get_session_stats, get_available_years
from chart_creators import create_lap_times_chart

def render_welcome_screen():
    """Welcome screen with latest race - always shown"""
    st.markdown("# 🏎️ Latest F1 Race Analysis")
    st.markdown("*Most recent race data with instant analysis*")
    
    latest_race = get_latest_race_data()
    
    if latest_race:
        session = latest_race['session']
        stats = get_session_stats(session)
        
        # Prominent header
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            title = f"🏁 **{latest_race['event']} {latest_race['year']}**"
            if latest_race['year'] >= 2025:
                title += " *(LIVE SEASON)*"
            st.markdown(f"## {title}")
            
            if latest_race['status'] == 'race_complete':
                st.success("✅ Race Complete - Full Analysis Available")
            else:
                st.info("🏁 Latest Qualifying - Live Data")
        
        with col2:
            st.metric("📅 Date", stats.get('session_date', 'Unknown'))
        with col3:
            st.metric("🏎️ Session", latest_race['session_type'])
        
        # Enhanced stats with better layout
        st.markdown("### 📊 Key Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏆 Fastest Driver", stats.get('fastest_lap_driver', 'N/A'))
        with col2:
            st.metric("⚡ Best Time", stats.get('fastest_lap_time', 'N/A'))
        with col3:
            st.metric("👥 Drivers", stats.get('total_drivers', 0))
        with col4:
            st.metric("🔄 Total Laps", stats.get('total_laps', 0))
        
        # Prominent auto-load button
        st.markdown("### 🔬 Deep Analysis")
        button_text = "🔬 Open Detailed Analysis Dashboard"
        if latest_race['year'] >= 2025:
            button_text = "🔬 Analyze Live 2025 Race Data"
            
        if st.button(button_text, type="primary", use_container_width=True):
            st.session_state.session = session
            st.session_state.event_info = f"{latest_race['event']} {latest_race['session_type']} ({latest_race['year']})"
            st.session_state.year = latest_race['year']
            st.rerun()
        
        # Auto-display race analysis
        if latest_race['session_type'] == 'R':
            st.markdown("### 🏁 Race Summary")
            
            try:
                final_positions = session.laps.groupby('Driver')['Position'].last().dropna()
                top_drivers = final_positions.sort_values().head(5).index.tolist()
                
                if top_drivers:
                    # Show lap times chart
                    fig = create_lap_times_chart(session, top_drivers)
                    fig.update_layout(height=450, title="Top 5 Drivers - Lap Time Progression")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Enhanced podium display
                    podium = final_positions.sort_values().head(3)
                    st.markdown("### 🏆 Race Podium")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if len(podium) > 0:
                            st.success(f"**🥇 WINNER**\n### {podium.index[0]}")
                    with col2:
                        if len(podium) > 1:
                            st.info(f"**🥈 SECOND**\n### {podium.index[1]}")
                    with col3:
                        if len(podium) > 2:
                            st.warning(f"**🥉 THIRD**\n### {podium.index[2]}")
                
            except:
                st.info("⏳ Loading race analysis...")
        
        elif latest_race['session_type'] == 'Q':
            st.markdown("### 🏁 Qualifying Results")
            
            try:
                fastest_laps = []
                for driver in session.laps['Driver'].unique():
                    try:
                        fastest_lap = session.laps.pick_driver(driver).pick_fastest()
                        lap_time_seconds = fastest_lap['LapTime'].total_seconds()
                        minutes = int(lap_time_seconds // 60)
                        seconds = lap_time_seconds % 60
                        formatted_time = f"{minutes}:{seconds:06.3f}"
                        
                        fastest_laps.append({
                            'Driver': driver,
                            'Time': formatted_time,
                            'Seconds': lap_time_seconds
                        })
                    except:
                        continue
                
                if fastest_laps:
                    df = pd.DataFrame(fastest_laps)
                    df = df.sort_values('Seconds').head(10)
                    df['Position'] = range(1, len(df) + 1)
                    
                    # Enhanced top 3 display
                    st.markdown("### 🏆 Qualifying Top 3")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if len(df) > 0:
                            st.success(f"**🥇 POLE POSITION**\n### {df.iloc[0]['Driver']}\n**{df.iloc[0]['Time']}**")
                    with col2:
                        if len(df) > 1:
                            st.info(f"**🥈 FRONT ROW**\n### {df.iloc[1]['Driver']}\n**{df.iloc[1]['Time']}**")
                    with col3:
                        if len(df) > 2:
                            st.warning(f"**🥉 THIRD**\n### {df.iloc[2]['Driver']}\n**{df.iloc[2]['Time']}**")
                    
                    # Full qualifying results table
                    st.markdown("### 📋 Complete Qualifying Results")
                    display_df = df[['Position', 'Driver', 'Time']].reset_index(drop=True)
                    st.dataframe(display_df, use_container_width=True, height=350)
                
            except:
                st.info("⏳ Loading qualifying analysis...")
        
        # Additional insights
        st.markdown("### 💡 Quick Insights")
        col1, col2 = st.columns(2)
        with col1:
            st.info("🔍 **Use the sidebar** to explore different races and sessions")
            st.info("📊 **Click 'Detailed Analysis'** for advanced telemetry and sector analysis")
        with col2:
            if latest_race['year'] >= 2025:
                st.success("🏁 **Live 2025 Season** - Real-time F1 data analysis")
            st.info("⚡ **Six analysis tabs** available: Lap times, sectors, telemetry, positions, speed traces, and data export")
    
    else:
        st.info("⏳ Loading latest F1 race data...")
        st.markdown("### 🔧 Manual Race Selection")
        st.markdown("**Use the sidebar to select any F1 race for analysis**")
        
        # Show available features while loading
        st.markdown("### 🚀 Available Analytics")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📊 Race Analysis:**")
            st.markdown("- Lap-by-lap performance tracking")
            st.markdown("- Position changes throughout race")
            st.markdown("- Tire strategy analysis")
        
        with col2:
            st.markdown("**🔧 Technical Analysis:**")
            st.markdown("- Sector time comparisons")
            st.markdown("- Speed traces around track")
            st.markdown("- Advanced telemetry data")
    
    # Always show quick start info
    available_years = get_available_years()
    if available_years and max(available_years) >= 2025:
        st.success("🏁 **Live 2025 F1 Season Available** - Use sidebar to explore all races!")
    else:
        st.info("💡 **Explore Historical F1 Data** - Use sidebar to browse past seasons")