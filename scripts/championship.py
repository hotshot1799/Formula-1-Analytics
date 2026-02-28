"""
Championship standings functions.
"""
import os
import sys

# Ensure the repo root is on the path so imports work when run standalone.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from team_colors import get_driver_color, initialize_session_colors
import logging
import fastf1

@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def get_current_championship_standings(year):
    """Get current driver championship standings for the year.

    Strategy: load only the most recent race and read cumulative Points
    from session.results. Falls back to loading up to 3 races if the
    most recent one lacks a Points column.
    """
    try:
        # Get the schedule for the year
        schedule = fastf1.get_event_schedule(year)
        if schedule.empty:
            return None

        events = schedule['EventName'].tolist()

        # For current year, only use past events
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        schedule['Session5DateUtc'] = pd.to_datetime(schedule['Session5DateUtc'], utc=True)
        past_schedule = schedule[schedule['Session5DateUtc'] <= now_utc]
        if not past_schedule.empty:
            events = past_schedule.sort_values('Session5DateUtc', ascending=False)['EventName'].tolist()

        if not events:
            return None

        driver_points = {}
        driver_full_names = {}

        # Fast path: load most recent race, read cumulative Points from results
        for event in events[:3]:  # Try up to 3 most recent events
            try:
                session = fastf1.get_session(year, event, 'R')
                session.load()

                if hasattr(session, 'results') and not session.results.empty:
                    results = session.results
                    if 'Points' in results.columns:
                        for _, row in results.iterrows():
                            if pd.notna(row.get('Abbreviation')) and pd.notna(row.get('Points')):
                                driver = row['Abbreviation']
                                driver_points[driver] = float(row['Points'])
                                if pd.notna(row.get('FullName')):
                                    driver_full_names[driver] = row['FullName']

                        if driver_points:
                            break  # Got cumulative standings from one race

            except Exception:
                continue

        # Slow fallback: if no cumulative Points column, sum race-by-race (cap at 3)
        if not driver_points:
            st.warning("Using slow fallback for championship standings (loading multiple races)")
            points_system = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}

            for event in events[:3]:
                try:
                    session = fastf1.get_session(year, event, 'R')
                    session.load()

                    if hasattr(session, 'laps') and not session.laps.empty:
                        final_positions = session.laps.groupby('Driver')['Position'].last().dropna()

                        for driver, position in final_positions.items():
                            try:
                                pos = int(position)
                                points = points_system.get(pos, 0)
                                if driver not in driver_points:
                                    driver_points[driver] = 0
                                driver_points[driver] += points
                            except Exception:
                                continue
                except Exception:
                    continue

        if not driver_points:
            return None

        # Create standings dataframe
        standings = []
        for driver, points in driver_points.items():
            full_name = driver_full_names.get(driver, driver)
            standings.append({
                'Driver': driver,
                'Full Name': full_name,
                'Points': points
            })

        df = pd.DataFrame(standings)
        df = df.sort_values('Points', ascending=False).reset_index(drop=True)
        df['Position'] = range(1, len(df) + 1)

        return df

    except Exception as e:
        st.error(f"Error getting championship standings: {e}")
        return None

def create_championship_chart(standings_df, year):
    """Create championship standings chart"""
    try:
        if standings_df is None or standings_df.empty:
            return None
        
        # Limit to top 15 drivers for readability
        top_drivers = standings_df.head(15)
        
        # Create horizontal bar chart
        fig = go.Figure()
        
        # Get colors for drivers (create a mock session for color assignment)
        colors = []
        for driver in top_drivers['Driver']:
            try:
                # Try to get team color, fallback to generic if not available
                color = get_driver_color(driver) if 'driver_colors' in st.session_state else px.colors.qualitative.Set3[len(colors) % len(px.colors.qualitative.Set3)]
                colors.append(color)
            except Exception:
                colors.append(px.colors.qualitative.Set3[len(colors) % len(px.colors.qualitative.Set3)])
        
        # Create horizontal bar chart
        fig.add_trace(go.Bar(
            y=[f"P{row['Position']} {row['Driver']}" for _, row in top_drivers.iterrows()],
            x=top_drivers['Points'],
            orientation='h',
            marker=dict(color=colors),
            hovertemplate='<b>%{y}</b><br>Points: %{x}<extra></extra>',
            showlegend=False
        ))
        
        # Update layout
        fig.update_layout(
            title=f"{year} Driver Championship Standings",
            xaxis_title="Championship Points",
            yaxis_title="Position & Driver",
            height=600,
            yaxis=dict(autorange='reversed'),  # Top position at top
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=150)  # More space for driver names
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating championship chart: {e}")
        return None

def create_championship_table(standings_df):
    """Create a clean championship table"""
    if standings_df is None or standings_df.empty:
        return None
    
    # Format for display
    display_df = standings_df.copy()
    
    # Create display name column
    if 'Full Name' in display_df.columns:
        display_df['Driver Name'] = display_df.apply(
            lambda row: f"{row['Full Name']}" if pd.notna(row['Full Name']) and row['Full Name'] != row['Driver'] else row['Driver'],
            axis=1
        )
    else:
        display_df['Driver Name'] = display_df['Driver']
    
    # Select columns for display
    table_df = display_df[['Position', 'Driver Name', 'Points']].copy()
    
    # Add styling for top 3
    def style_top_three(row):
        if row['Position'] == 1:
            return ['background-color: #FFD700; font-weight: bold'] * len(row)  # Gold
        elif row['Position'] == 2:
            return ['background-color: #C0C0C0; font-weight: bold'] * len(row)  # Silver  
        elif row['Position'] == 3:
            return ['background-color: #CD7F32; font-weight: bold'] * len(row)  # Bronze
        else:
            return [''] * len(row)
    
    return table_df

def render_championship_section(year):
    """Render the championship standings section"""
    st.markdown("### 🏆 Current Championship Standings")
    
    with st.spinner("Loading championship standings..."):
        standings_df = get_current_championship_standings(year)
    
    if standings_df is not None and not standings_df.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Championship chart
            fig = create_championship_chart(standings_df, year)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Championship table and top 3
            st.markdown("#### 🥇 Top 3 Drivers")
            
            top_3 = standings_df.head(3)
            for i, (_, row) in enumerate(top_3.iterrows()):
                if i == 0:
                    st.success(f"🥇 **{row['Driver']}** - {row['Points']} pts")
                elif i == 1:
                    st.info(f"🥈 **{row['Driver']}** - {row['Points']} pts")
                else:
                    st.warning(f"🥉 **{row['Driver']}** - {row['Points']} pts")
            
            # Points gap analysis
            if len(standings_df) > 1:
                leader_points = standings_df.iloc[0]['Points']
                second_points = standings_df.iloc[1]['Points']
                gap = leader_points - second_points
                
                st.markdown("#### 📊 Championship Battle")
                if gap == 0:
                    st.info("🔥 **Tied for the lead!**")
                elif gap <= 25:
                    st.warning(f"🔥 **Close battle!** {gap} point gap")
                else:
                    st.info(f"📈 **Leader ahead by {gap} points**")
        
        # Full standings table
        st.markdown("#### 📋 Complete Standings")
        table_df = create_championship_table(standings_df)
        if table_df is not None:
            st.dataframe(table_df, use_container_width=True, height=400)
        
        # Championship insights
        if year >= 2025:
            st.success(f"🏁 **Live {year} Championship** - Updated with latest race results")
        else:
            st.info(f"📚 **{year} Final Championship** - Complete season results")
    
    else:
        st.warning("⚠️ Championship standings not available")
        st.info("💡 **Possible reasons:**")
        st.markdown("- Season hasn't started yet")
        st.markdown("- No race results available") 
        st.markdown("- Data not yet processed")
        
        # Show placeholder
        st.markdown("### 🏁 Championship Preview")
        st.info("Championship standings will appear here once race data is available")

def get_championship_leader(year):
    """Get the current championship leader"""
    try:
        standings_df = get_current_championship_standings(year)
        if standings_df is not None and not standings_df.empty:
            leader = standings_df.iloc[0]
            return {
                'driver': leader['Driver'],
                'full_name': leader.get('Full Name', leader['Driver']),
                'points': leader['Points']
            }
        return None
    except Exception:
        return None