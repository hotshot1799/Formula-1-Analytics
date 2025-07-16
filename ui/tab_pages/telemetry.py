"""
Telemetry analysis tab
"""
import streamlit as st
from chart_creators import create_telemetry_chart
from analysis_utils import get_telemetry_insights

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