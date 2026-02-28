"""
Telemetry analysis tab.
"""
import streamlit as st
from chart_creators import create_telemetry_chart
from analysis_utils import get_telemetry_insights
from data_loader import load_session


def render_telemetry_tab(session):
    """Render telemetry analysis tab."""
    st.header("Advanced Telemetry Analysis")

    available_drivers = session.laps['Driver'].unique().tolist()

    if len(available_drivers) < 2:
        st.warning("Need at least 2 drivers for telemetry comparison")
        return

    # Check telemetry availability
    telemetry_available = False
    try:
        sample_lap = session.laps.pick_fastest()
        tel_sample = sample_lap.get_telemetry()
        if not tel_sample.empty and 'Speed' in tel_sample.columns:
            telemetry_available = True
    except Exception:
        pass

    if not telemetry_available:
        st.warning("Telemetry data not available in the current session.")
        _try_fallback_sessions()
        return

    try:
        _render_telemetry_comparison(session, available_drivers)
    except Exception as e:
        st.error(f"Error creating telemetry analysis: {e}")


def _try_fallback_sessions():
    """Try loading telemetry from alternate sessions of the same GP.

    Checks each candidate silently behind a single spinner and only
    shows one message at the end — either success (with a rerun) or a
    single error.
    """
    current = st.session_state.get('session_type', '')
    candidates = [s for s in ['Q', 'FP3', 'FP2', 'FP1', 'R'] if s != current]

    with st.spinner("Searching other sessions for telemetry data..."):
        for alt_type in candidates:
            try:
                alt_session = load_session(
                    st.session_state.year, st.session_state.event, alt_type
                )
                if not alt_session:
                    continue
                alt_tel = alt_session.laps.pick_fastest().get_telemetry()
                if not alt_tel.empty and 'Speed' in alt_tel.columns:
                    st.session_state.session = alt_session
                    st.session_state.session_type = alt_type
                    st.session_state.event_info = (
                        f"{st.session_state.event} {alt_type} "
                        f"({st.session_state.year}) - Telemetry Fallback"
                    )
                    st.success(f"Telemetry found in {alt_type} session — reloading.")
                    st.rerun()
            except Exception:
                continue

    st.error(
        "No telemetry available for any session in this GP. "
        "Try selecting an older Grand Prix via the sidebar."
    )


def _render_telemetry_comparison(session, available_drivers):
    col1, col2 = st.columns(2)
    with col1:
        driver1 = st.selectbox("Primary Driver", available_drivers, key="tel_driver1")
    with col2:
        others = [d for d in available_drivers if d != driver1]
        driver2 = st.selectbox("Comparison Driver", others, key="tel_driver2")

    if driver1 == driver2:
        st.warning("Please select two different drivers for comparison")
        return

    with st.spinner(f"Loading telemetry for {driver1} vs {driver2}..."):
        fig = create_telemetry_chart(session, driver1, driver2)

    if not fig:
        st.warning("Telemetry data not available for selected drivers")
        return

    st.plotly_chart(fig, use_container_width=True)

    insights = get_telemetry_insights(session, driver1, driver2)
    if insights:
        col1, col2 = st.columns(2)
        for col, driver in [(col1, driver1), (col2, driver2)]:
            with col:
                st.markdown(f"### {driver}")
                st.metric("Max Speed", f"{insights[driver]['max_speed']:.1f} km/h")
                st.metric("Avg Speed", f"{insights[driver]['avg_speed']:.1f} km/h")
                if insights[driver]['avg_throttle']:
                    st.metric("Avg Throttle", f"{insights[driver]['avg_throttle']:.1f}%")
