"""
Telemetry analysis tab
"""
import streamlit as st
from chart_creators import create_telemetry_chart
from analysis_utils import get_telemetry_insights
from data_loader import load_session

def render_telemetry_tab(session):
    """Render telemetry analysis tab"""
    st.header("📈 Advanced Telemetry Analysis")
    
    available_drivers = session.laps['Driver'].unique().tolist()
    
    if len(available_drivers) >= 2:
        # Add this new block for GP-specific telemetry handling
        telemetry_available = False
        try:
            # Quick check for telemetry in current session
            sample_lap = session.laps.pick_fastest()
            tel_sample = sample_lap.get_telemetry()
            if not tel_sample.empty and 'Speed' in tel_sample.columns:
                telemetry_available = True
        except:
            pass

        if not telemetry_available:
            st.warning("⚠️ Telemetry data not available in the current session (common for recent 2025 sessions).")
            
            # Try other sessions from the same GP
            session_types_to_try = ['Q', 'FP3', 'FP2', 'FP1'] if st.session_state.session_type == 'R' else ['R', 'Q', 'FP3', 'FP2', 'FP1']
            session_types_to_try = [s for s in session_types_to_try if s != st.session_state.session_type]  # Skip current
            
            for alt_type in session_types_to_try:
                st.info(f"Checking {alt_type} session for this GP...")
                with st.spinner(f"Loading {alt_type} telemetry..."):
                    alt_session = load_session(st.session_state.year, st.session_state.event, alt_type)
                    if alt_session:
                        try:
                            alt_sample_lap = alt_session.laps.pick_fastest()
                            alt_tel = alt_sample_lap.get_telemetry()
                            if not alt_tel.empty and 'Speed' in alt_tel.columns:
                                st.session_state.session = alt_session
                                st.session_state.session_type = alt_type
                                st.session_state.event_info = f"{st.session_state.event} {alt_type} ({st.session_state.year}) - Telemetry Fallback"
                                st.success(f"✅ Telemetry loaded from {alt_type} session of this GP!")
                                st.rerun()
                        except:
                            continue
            
            # If none found
            st.error("❌ No telemetry available for any session in this GP. Try selecting an older Grand Prix via the sidebar (e.g., 2024 events often have full data).")
            return  # Stop rendering if no telemetry
        
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
                    
                    # Add comparison insights
                    try:
                        speed_diff = insights[driver1]['max_speed'] - insights[driver2]['max_speed']
                        if abs(speed_diff) > 1:
                            faster_driver = driver1 if speed_diff > 0 else driver2
                            st.info(f"🏁 **Speed Advantage**: {faster_driver} had {abs(speed_diff):.1f} km/h higher max speed")
                        
                        # Throttle comparison
                        if insights[driver1]['avg_throttle'] and insights[driver2]['avg_throttle']:
                            throttle_diff = insights[driver1]['avg_throttle'] - insights[driver2]['avg_throttle']
                            if abs(throttle_diff) > 2:
                                aggressive_driver = driver1 if throttle_diff > 0 else driver2
                                st.info(f"🔥 **Driving Style**: {aggressive_driver} used {abs(throttle_diff):.1f}% more throttle on average")
                    except:
                        pass
                
                # Telemetry tips
                st.subheader("💡 Telemetry Analysis Tips")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info("🔍 **What to Look For**")
                    st.markdown("- **Speed traces**: Compare top speeds and acceleration")
                    st.markdown("- **Braking points**: Earlier braking = more conservative")
                    st.markdown("- **Throttle application**: Smooth vs aggressive styles")
                
                with col2:
                    st.info("📊 **Interpretation**")
                    st.markdown("- **Higher max speed**: Better straight-line pace")
                    st.markdown("- **Consistent throttle**: Smoother driving style")
                    st.markdown("- **Gear changes**: Optimal shift points")
                
            else:
                st.warning("⚠️ Telemetry data not available for selected drivers")
                st.info("💡 **Telemetry availability:**")
                st.markdown("- Most available in recent races (2020+)")
                st.markdown("- Qualifying and practice sessions often have more data")
                st.markdown("- Some older races may have limited telemetry")
                st.markdown("- Try different drivers or sessions")
        else:
            st.warning("Please select two different drivers for comparison")
    else:
        st.warning("⚠️ Need at least 2 drivers for telemetry comparison")
        st.info(f"This session has {len(available_drivers)} driver(s)")
        st.markdown("**Telemetry analysis requires:**")
        st.markdown("- At least 2 drivers in the session")
        st.markdown("- Available telemetry data for comparison")
        st.markdown("- Try a different session with more drivers")