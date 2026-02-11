"""
Speed traces analysis tab
"""
import streamlit as st
from chart_creators import create_speed_trace_chart

def render_speed_traces_tab(session):
    """Render speed traces tab"""
    st.header("🎯 Speed Trace Analysis")
    
    available_drivers = session.laps['Driver'].unique().tolist()
    
    if not available_drivers:
        st.error("No drivers found in this session")
        return
    
    # Driver selection with smart defaults
    default_count = min(3, len(available_drivers))
    trace_drivers = st.multiselect(
        "Select drivers for speed trace analysis (max 5):",
        available_drivers,
        default=available_drivers[:default_count],
        max_selections=5,
        help="Compare speed variations around the track for fastest laps"
    )
    
    if trace_drivers:
        with st.spinner("Generating speed traces..."):
            fig = create_speed_trace_chart(session, trace_drivers)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            # Speed trace insights
            st.subheader("🔍 Speed Trace Analysis")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("💡 **Speed Trace Insights**")
                st.markdown("- Shows speed variations for **fastest laps**")
                st.markdown("- **High speed sections**: Long straights and fast corners")
                st.markdown("- **Low speed sections**: Tight corners and chicanes")
                st.markdown("- **Smooth lines**: Consistent driving style")
            
            with col2:
                st.info("🏁 **Track Analysis**")
                st.markdown("- **Compare braking points**: Where speed drops rapidly")
                st.markdown("- **Acceleration zones**: Where drivers gain speed")
                st.markdown("- **Corner exit speed**: Critical for lap time")
                st.markdown("- **DRS zones**: Higher top speeds on straights")
            
            # Advanced analysis tips
            st.subheader("📊 Advanced Speed Analysis")
            
            with st.expander("🔬 How to Read Speed Traces"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🟢 What Good Speed Traces Show:**")
                    st.markdown("- Smooth speed transitions")
                    st.markdown("- High corner exit speeds")
                    st.markdown("- Late braking points")
                    st.markdown("- Optimal DRS usage")
                
                with col2:
                    st.markdown("**🔴 Performance Issues:**")
                    st.markdown("- Jagged speed lines (inconsistent)")
                    st.markdown("- Early braking (too conservative)")
                    st.markdown("- Low corner exit speeds")
                    st.markdown("- Poor straight-line speed")
            
            # Track-specific insights
            try:
                # Get session info for track-specific tips
                track_name = session.session_info.get('Location', '') if hasattr(session, 'session_info') else ''
                
                st.subheader("🏁 Track-Specific Tips")
                
                if 'Monaco' in track_name:
                    st.info("🏰 **Monaco**: Focus on corner exit speeds - every mph counts on this tight circuit")
                elif 'Monza' in track_name:
                    st.info("🏎️ **Monza**: Look for slipstream effects and DRS performance on long straights")
                elif 'Silverstone' in track_name:
                    st.info("🇬🇧 **Silverstone**: High-speed corners require different approach - check Copse and Maggotts/Becketts")
                else:
                    st.info("🏁 **General**: Compare how drivers handle the fastest and slowest sections of the track")
                    
            except Exception:
                pass
        
        else:
            st.warning("⚠️ Speed trace data not available for selected drivers")
            st.info("💡 **Speed trace requirements:**")
            st.markdown("- Telemetry data must be available")
            st.markdown("- Distance measurements required")
            st.markdown("- Try recent races (2020+) for best data")
            st.markdown("- Qualifying sessions often have cleaner data")
    
    else:
        st.warning("Please select at least one driver for speed trace analysis")
        st.markdown("**Speed trace analysis shows:**")
        st.markdown("- 🏎️ Speed variations around the entire track")
        st.markdown("- 🎯 Braking and acceleration points")
        st.markdown("- 📊 Driver-to-driver comparison on fastest laps")
        st.markdown("- 🏁 Track-specific performance insights")