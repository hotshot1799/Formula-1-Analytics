"""
Lap analysis tab
"""
import streamlit as st
from chart_creators import create_lap_times_chart
from analysis_utils import calculate_lap_statistics

def render_lap_analysis_tab(session):
    """Render lap analysis tab"""
    st.header("📊 Lap Time Analysis")
    
    all_drivers = session.laps['Driver'].unique().tolist()
    
    # Driver selection
    default_count = min(5, len(all_drivers))
    selected_drivers = st.multiselect(
        "Select drivers (max 10):", 
        all_drivers, 
        default=all_drivers[:default_count],
        max_selections=10
    )
    
    if selected_drivers:
        with st.spinner("Creating analysis..."):
            fig = create_lap_times_chart(session, selected_drivers)
            st.plotly_chart(fig, use_container_width=True)
        
        # Statistics
        st.subheader("📈 Statistics")
        lap_stats_df = calculate_lap_statistics(session, selected_drivers)
        
        if lap_stats_df is not None:
            st.dataframe(lap_stats_df, use_container_width=True)
        else:
            st.warning("No statistics available")
    else:
        st.warning("Select at least one driver")