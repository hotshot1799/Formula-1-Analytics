"""
Welcome screen for the F1 Analytics Dashboard.

Two modes:
  - No session loaded  -> show latest race with invitation to explore
  - Session loaded     -> show analysis for the loaded session
"""
import streamlit as st
from data_loader import get_latest_race_data, get_session_stats, get_available_years
from ui.components import render_podium, render_qualifying_results, render_fastest_times


_SESSION_NAMES = {
    'R': 'Race Session',
    'Q': 'Qualifying Session',
    'S': 'Sprint Session',
    'FP1': 'Free Practice 1',
    'FP2': 'Free Practice 2',
    'FP3': 'Free Practice 3',
}


def render_welcome_screen():
    """Context-aware welcome screen."""
    if 'session' in st.session_state:
        _render_loaded_session()
    else:
        _render_no_session()


# ── shared helpers ──────────────────────────────────────────────────────


def _render_stats_row(stats: dict) -> None:
    """Four-column key statistics row."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Fastest Driver", stats.get('fastest_lap_driver', 'N/A'))
    with col2:
        st.metric("Best Time", stats.get('fastest_lap_time', 'N/A'))
    with col3:
        st.metric("Drivers", stats.get('total_drivers', 0))
    with col4:
        st.metric("Total Laps", stats.get('total_laps', 0))


def _render_tools_reminder() -> None:
    """Available analysis tools section (written once)."""
    st.markdown("### Available Analysis Tools")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Seven Analysis Tabs Available:**")
        st.markdown(
            "- Lap Analysis - Detailed lap time tracking\n"
            "- Sector Times - Sector-by-sector performance\n"
            "- Telemetry - Advanced car data analysis\n"
            "- Tyre Analysis - Compound usage and strategy"
        )
    with col2:
        st.info("**Advanced Analysis:**")
        st.markdown(
            "- Position Tracking - Race position changes\n"
            "- Speed Traces - Track speed analysis\n"
            "- Data Export - Download race data"
        )


def _render_session_results(session, session_type: str) -> None:
    """Display results appropriate to the session type."""
    if session_type == 'R':
        st.markdown("### Race Results")
        try:
            if hasattr(session, 'laps') and not session.laps.empty:
                final_positions = (
                    session.laps.groupby('Driver')['Position'].last().dropna()
                )
                if not final_positions.empty:
                    podium = final_positions.sort_values().head(3)
                    render_podium(list(podium.index))
        except Exception:
            st.info("Loading race analysis...")

    elif session_type == 'Q':
        st.markdown("### Qualifying Results")
        try:
            render_qualifying_results(session)
        except Exception:
            st.info("Loading qualifying analysis...")

    else:
        name = _SESSION_NAMES.get(session_type, 'Session')
        st.markdown(f"### {name} Results")
        try:
            render_fastest_times(session)
        except Exception:
            st.info("Loading session analysis...")


def _render_track_info(stats: dict) -> None:
    if stats.get('track_name') and stats.get('track_name') != 'Unknown':
        st.info(f"**Track**: {stats.get('track_name')}")


# ── main modes ──────────────────────────────────────────────────────────


def _render_loaded_session() -> None:
    """Render analysis for the currently loaded session."""
    session = st.session_state.session
    event_info = st.session_state.get('event_info', 'Unknown Race')
    year = st.session_state.get('year', 'Unknown')
    event = st.session_state.get('event', 'Unknown')
    session_type = st.session_state.get('session_type', 'Unknown')
    stats = get_session_stats(session)

    st.markdown("# Race Analysis Dashboard")
    st.markdown(f"*Currently Analyzing: {event_info}*")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        title = f"**{event} {year}**"
        if isinstance(year, int) and year >= 2025:
            title += " *(LIVE SEASON)*"
        st.markdown(f"## {title}")
        session_name = _SESSION_NAMES.get(session_type, f"{session_type} Session")
        if session_type == 'R':
            st.success(f"{session_name} - Full Race Analysis")
        else:
            st.info(f"{session_name}")
    with col2:
        st.metric("Date", stats.get('session_date', 'Unknown'))
    with col3:
        if st.button("Back to Latest", help="Return to latest race overview"):
            for key in ['session', 'event_info', 'year', 'event', 'session_type']:
                st.session_state.pop(key, None)
            st.rerun()

    st.markdown("### Session Statistics")
    _render_stats_row(stats)
    _render_track_info(stats)
    _render_session_results(session, session_type)
    _render_tools_reminder()


def _render_no_session() -> None:
    """Show latest race data with an invitation to explore."""
    st.markdown("# Latest F1 Race Analysis")
    st.markdown("*Most recent race data with instant analysis*")
    st.info("**Load a specific race** using the sidebar to replace this view with detailed analysis")

    latest_race = get_latest_race_data()

    if latest_race:
        session = latest_race['session']
        stats = get_session_stats(session)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            title = f"**{latest_race['event']} {latest_race['year']}**"
            if latest_race['year'] >= 2025:
                title += " *(LIVE SEASON)*"
            st.markdown(f"## {title}")
            if latest_race['status'] == 'race_complete':
                st.success("Race Complete - Full Analysis Available")
            else:
                st.info("Latest Qualifying - Live Data")
        with col2:
            st.metric("Date", stats.get('session_date', 'Unknown'))
        with col3:
            st.metric("Session", latest_race['session_type'])

        st.markdown("### Key Statistics")
        _render_stats_row(stats)

        button_text = "Open Detailed Analysis Dashboard"
        if latest_race['year'] >= 2025:
            button_text = "Analyze Live 2025 Race Data"
        if st.button(button_text, type="primary", use_container_width=True):
            st.session_state.session = session
            st.session_state.event_info = (
                f"{latest_race['event']} {latest_race['session_type']} ({latest_race['year']})"
            )
            st.session_state.year = latest_race['year']
            st.session_state.event = latest_race['event']
            st.session_state.session_type = latest_race['session_type']
            st.rerun()

        _render_session_results(session, latest_race['session_type'])

    else:
        st.info("Loading latest F1 race data...")
        st.markdown("### Manual Race Selection")
        st.markdown("**Use the sidebar to select any F1 race for analysis**")

    available_years = get_available_years()
    if available_years and max(available_years) >= 2025:
        st.success("**Live 2025 F1 Season Available** - Use sidebar to explore all races!")
    else:
        st.info("**Explore Historical F1 Data** - Use sidebar to browse past seasons")
