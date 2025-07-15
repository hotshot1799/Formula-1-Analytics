"""
F1 2025 Data Debug Script
Run this to diagnose 2025 data access issues
"""

import streamlit as st
import fastf1
import pandas as pd
import tempfile
import warnings
from datetime import datetime

def debug_2025_data():
    """Comprehensive debug of 2025 F1 data access"""
    st.title("🔧 F1 2025 Data Debug Tool")
    
    # Step 1: Test FastF1 Installation
    st.header("1. 📦 FastF1 Installation Check")
    try:
        st.success(f"✅ FastF1 version: {fastf1.__version__}")
    except Exception as e:
        st.error(f"❌ FastF1 import error: {e}")
        return
    
    # Step 2: Test Basic 2025 Schedule Access
    st.header("2. 📅 2025 Schedule Access Test")
    try:
        schedule = fastf1.get_event_schedule(2025)
        if schedule.empty:
            st.error("❌ 2025 schedule is empty")
            st.info("💡 Try: pip install --upgrade fastf1")
            return
        else:
            st.success(f"✅ 2025 schedule loaded: {len(schedule)} events")
            
            # Show recent events
            events = schedule['EventName'].tolist()
            st.write("**Recent 2025 events:**")
            for event in events[-5:]:
                st.write(f"- {event}")
                
    except Exception as e:
        st.error(f"❌ Schedule error: {e}")
        st.info("💡 This suggests FastF1 doesn't have 2025 data yet")
        return
    
    # Step 3: Test Specific Race Access
    st.header("3. 🏁 Specific Race Data Test")
    
    # Test races in order of likelihood to have data
    test_races = [
        "British Grand Prix",
        "Austrian Grand Prix", 
        "Canadian Grand Prix",
        "Spanish Grand Prix",
        "Monaco Grand Prix"
    ]
    
    working_races = []
    
    for race in test_races:
        try:
            # Test if race exists in schedule
            if race not in events:
                st.warning(f"⚠️ {race}: Not in 2025 schedule")
                continue
                
            # Try to get session
            session = fastf1.get_session(2025, race, 'R')
            
            # Check if session has date
            if hasattr(session, 'date') and session.date:
                st.info(f"📅 {race}: Session date {session.date}")
                
                # Try to load data
                session.load()
                
                if hasattr(session, 'laps') and not session.laps.empty:
                    lap_count = len(session.laps)
                    driver_count = len(session.laps['Driver'].unique())
                    st.success(f"✅ {race}: {lap_count} laps, {driver_count} drivers")
                    working_races.append(race)
                else:
                    st.warning(f"⚠️ {race}: No lap data")
            else:
                st.info(f"📋 {race}: No session date info")
                
        except Exception as e:
            error_msg = str(e)
            if "not yet available" in error_msg.lower():
                st.info(f"⏳ {race}: Data not yet available")
            elif "no data" in error_msg.lower():
                st.warning(f"📊 {race}: No data found") 
            else:
                st.error(f"❌ {race}: {error_msg[:100]}")
    
    # Step 4: Alternative Data Sources
    st.header("4. 🔄 Alternative Solutions")
    
    if not working_races:
        st.error("❌ No 2025 race data found")
        
        st.markdown("### Possible Solutions:")
        
        # Solution 1: Check FastF1 version
        st.markdown("**1. Update FastF1:**")
        st.code("pip install --upgrade fastf1", language="bash")
        
        # Solution 2: Try 2024 data
        st.markdown("**2. Use 2024 data temporarily:**")
        if st.button("Test 2024 Data"):
            test_2024_fallback()
        
        # Solution 3: Check if 2025 season has started
        st.markdown("**3. Season Status Check:**")
        current_date = datetime.now()
        if current_date.month < 3:  # Before March
            st.info("🗓️ 2025 F1 season may not have started yet")
        elif current_date.month >= 12:  # After season
            st.info("🏁 2025 F1 season may have ended")
        
        # Solution 4: Manual data entry
        st.markdown("**4. Manual Override:**")
        if st.button("Enable 2024 Mode"):
            st.session_state.fallback_year = 2024
            st.success("✅ Switched to 2024 data mode")
    
    else:
        st.success(f"🎉 Found working 2025 races: {', '.join(working_races)}")
        
        # Test the best working race
        if st.button(f"Load {working_races[0]} for Analysis"):
            load_working_race(working_races[0])

def test_2024_fallback():
    """Test 2024 data as fallback"""
    st.subheader("🔄 Testing 2024 Data Fallback")
    
    try:
        # Test 2024 schedule
        schedule_2024 = fastf1.get_event_schedule(2024)
        if not schedule_2024.empty:
            st.success(f"✅ 2024 schedule: {len(schedule_2024)} events")
            
            # Test recent 2024 race
            events_2024 = schedule_2024['EventName'].tolist()
            test_race = events_2024[-1]  # Last race of 2024
            
            session = fastf1.get_session(2024, test_race, 'R')
            session.load()
            
            if hasattr(session, 'laps') and not session.laps.empty:
                st.success(f"✅ 2024 {test_race}: {len(session.laps)} laps available")
                st.info("💡 Your app can use 2024 data while waiting for 2025 data")
            else:
                st.warning("⚠️ 2024 data also has issues")
        else:
            st.error("❌ 2024 schedule also empty")
            
    except Exception as e:
        st.error(f"❌ 2024 test failed: {e}")

def load_working_race(race_name):
    """Load a working race into session state"""
    try:
        session = fastf1.get_session(2025, race_name, 'R')
        session.load()
        
        if hasattr(session, 'laps') and not session.laps.empty:
            # Store in session state
            st.session_state.session = session
            st.session_state.event_info = f"{race_name} R (2025)"
            st.session_state.year = 2025
            
            st.success(f"🎉 Successfully loaded {race_name}!")
            st.info("You can now go back to the main app and analyze this race")
            
            # Show quick stats
            lap_count = len(session.laps)
            driver_count = len(session.laps['Driver'].unique())
            st.metric("Total Laps", lap_count)
            st.metric("Drivers", driver_count)
        else:
            st.error("❌ Failed to load race data")
            
    except Exception as e:
        st.error(f"❌ Loading error: {e}")

def quick_fix_suggestions():
    """Show quick fix suggestions"""
    st.header("🚀 Quick Fixes to Try")
    
    fixes = [
        {
            "title": "1. Update FastF1",
            "command": "pip install --upgrade fastf1",
            "description": "Get the latest version with 2025 support"
        },
        {
            "title": "2. Clear Cache", 
            "command": "import fastf1; fastf1.Cache.clear_cache()",
            "description": "Clear cached data that might be corrupted"
        },
        {
            "title": "3. Use Different Ergast API",
            "command": "fastf1.ergast.interface.BASE_URL = 'http://ergast.com/api/f1'",
            "description": "Try the original Ergast API"
        },
        {
            "title": "4. Install from GitHub",
            "command": "pip install git+https://github.com/theOehrly/Fast-F1.git",
            "description": "Get the very latest development version"
        }
    ]
    
    for fix in fixes:
        with st.expander(fix["title"]):
            st.code(fix["command"], language="bash")
            st.write(fix["description"])

def main():
    """Main debug function"""
    
    # Quick status check
    st.sidebar.header("🔧 Debug Status")
    
    if st.sidebar.button("🧪 Run Full Debug"):
        debug_2025_data()
    
    if st.sidebar.button("💡 Show Quick Fixes"):
        quick_fix_suggestions()
    
    # Check if we have a fallback mode
    if 'fallback_year' in st.session_state:
        st.sidebar.warning(f"⚠️ Using {st.session_state.fallback_year} data mode")
        if st.sidebar.button("🔄 Try 2025 Again"):
            del st.session_state.fallback_year
            st.rerun()

if __name__ == "__main__":
    main()