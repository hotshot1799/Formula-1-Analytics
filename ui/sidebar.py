"""
Sidebar component - pure lazy loading
"""
import streamlit as st
from data_loader import get_available_years, get_schedule, load_session

def render_sidebar():
    """Render sidebar with lazy loading"""
    st.sidebar.header("⚙️ Session Selection")
    
    # Year selection
    available_years = get_available_years()
    if not available_years:
        st.sidebar.error("No F1 data available")
        return None, None, None, None
    
    year = st.sidebar.selectbox("Season", available_years)
    
    # Load events
    with st.spinner(f"Loading {year} schedule..."):
        events = get_schedule(year)
    
    if not events:
        st.sidebar.error(f"No events for {year}")
        return year, None, None, None
    
    # Status display
    if year >= 2025:
        st.sidebar.success(f"🏁 {year} LIVE!")
        st.sidebar.info(f"📅 {len(events)} races")
    elif year == 2024:
        st.sidebar.success("🏆 Complete 2024")
    else:
        st.sidebar.info(f"📚 {year} Historical")
    
    # Event selection
    if len(events) > 10:
        events = list(reversed(events))  # Recent first
    
    event = st.sidebar.selectbox("Race Event", events)
    
    # Session selection
    sessions = {
        'R': 'Race', 'Q': 'Qualifying', 'S': 'Sprint',
        'FP3': 'FP3', 'FP2': 'FP2', 'FP1': 'FP1'
    }
    
    session_type = st.sidebar.selectbox(
        "Session",
        list(sessions.keys()),
        format_func=lambda x: f"{x} - {sessions[x]}"
    )
    
    # Load button
    if st.sidebar.button(f"🔄 Load Data", type="primary", use_container_width=True):
        with st.spinner(f"Loading {event} {session_type}..."):
            session = load_session(year, event, session_type)
        
        if session:
            st.session_state.session = session
            st.session_state.event_info = f"{event} {session_type} ({year})"
            st.session_state.year = year
            st.sidebar.success("✅ Loaded!")
            
            # Show info
            if hasattr(session, 'laps') and not session.laps.empty:
                drivers = len(session.laps['Driver'].unique())
                laps = len(session.laps)
                st.sidebar.info(f"📊 {drivers} drivers, {laps} laps")
        else:
            st.sidebar.error("❌ No data available")
            if session_type == 'R':
                st.sidebar.info("💡 Try 'Q' instead")
    
    # Current session
    if 'session' in st.session_state:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Current")
        st.sidebar.info(st.session_state.event_info)
    
    return year, event, session_type, events