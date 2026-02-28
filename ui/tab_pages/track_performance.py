"""
Track performance analysis: sector times and speed traces.

Merged from the former sector_analysis.py and speed_traces.py.
"""
import streamlit as st
from chart_creators import create_sector_analysis_chart, create_speed_trace_chart
from analysis_utils import get_fastest_sector_times


# ── Sector Analysis ─────────────────────────────────────────────────────

def render_sector_analysis_tab(session):
    """Render sector analysis tab."""
    st.header("Sector Time Analysis")

    try:
        with st.spinner("Analyzing sector times..."):
            result = create_sector_analysis_chart(session)

        if result[0]:
            fig, df = result
            st.plotly_chart(fig, use_container_width=True)

            fastest_s1, fastest_s2, fastest_s3 = get_fastest_sector_times(df)
            if fastest_s1 is not None:
                st.subheader("Sector Champions")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Fastest Sector 1", fastest_s1['Driver'], f"{fastest_s1['Sector1']:.3f}s")
                with c2:
                    st.metric("Fastest Sector 2", fastest_s2['Driver'], f"{fastest_s2['Sector2']:.3f}s")
                with c3:
                    st.metric("Fastest Sector 3", fastest_s3['Driver'], f"{fastest_s3['Sector3']:.3f}s")

            st.subheader("Detailed Sector Times")
            st.dataframe(df.round(3), use_container_width=True)
        else:
            st.warning("No sector time data available for this session")
    except Exception as e:
        st.error(f"Error in sector analysis: {e}")


# ── Speed Traces ────────────────────────────────────────────────────────

def render_speed_traces_tab(session):
    """Render speed traces tab."""
    st.header("Speed Trace Analysis")

    available_drivers = session.laps['Driver'].unique().tolist()
    if not available_drivers:
        st.warning("No drivers found in this session")
        return

    default_count = min(3, len(available_drivers))
    trace_drivers = st.multiselect(
        "Select drivers for speed trace analysis (max 5):",
        available_drivers,
        default=available_drivers[:default_count],
        max_selections=5,
    )

    if not trace_drivers:
        st.warning("Please select at least one driver for speed trace analysis")
        return

    try:
        with st.spinner("Generating speed traces..."):
            fig = create_speed_trace_chart(session, trace_drivers)

        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Speed trace data not available for selected drivers")
    except Exception as e:
        st.error(f"Error creating speed traces: {e}")
