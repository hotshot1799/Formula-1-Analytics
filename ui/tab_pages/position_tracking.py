"""
Position tracking tab - fixed for better data handling
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from analysis_utils import get_position_data_safe, calculate_position_changes
from data_loader import load_session

def render_position_tracking_tab(session):
    """Render position tracking tab with enhanced data handling"""
    st.header("🏁 Race Position Tracking")
    
    # Check if this is a race session
    session_type = st.session_state.get('session_type', 'Unknown')

    if session_type != 'R':
        st.info("📋 Position tracking is only available for race sessions")
        if st.button("Load Race Session Instead"):
            with st.spinner("Loading race data..."):
                race_session = load_session(st.session_state.year, st.session_state.event, 'R')
                if race_session and hasattr(race_session, 'laps') and not race_session.laps.empty:
                    st.session_state.session = race_session
                    st.session_state.session_type = 'R'
                    st.session_state.event_info = f"{st.session_state.event} R ({st.session_state.year})"
                    st.success("✅ Race session loaded!")
                    st.rerun()
                else:
                    st.error("❌ No race data available for this event. Try selecting a different race.")
    else:
        # Try to get position data
        with st.spinner("Analyzing race positions..."):
            position_df = get_position_data_safe(session)
        
        if position_df is None or position_df.empty:
            st.warning("⚠️ No position data available for this race")
            st.info("💡 **Possible reasons:**")
            st.markdown("- Position data not recorded for this session")
            st.markdown("- Data may be incomplete or corrupted")
            st.markdown("- Try a different race session")
            
            # Show what data is available
            if hasattr(session, 'laps') and not session.laps.empty:
                available_cols = list(session.laps.columns)
                st.markdown("**Available data columns:**")
                st.write(available_cols)
            return
        
        # Show data summary
        st.success(f"✅ Position data loaded: {len(position_df)} position records")
        
        # Create position tracking chart
        try:
            fig = create_position_chart(position_df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            # Calculate and show position changes
            changes_df = calculate_position_changes(position_df)
            
            if changes_df is not None and not changes_df.empty:
                st.subheader("📊 Position Changes Summary")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📈 Biggest Gainers")
                    gainers = changes_df[changes_df['Positions Gained'] > 0].head(5)
                    if not gainers.empty:
                        for _, row in gainers.iterrows():
                            name = row.get('Full Name', row['Driver'])
                            st.success(f"🔥 **{name}**: +{row['Positions Gained']} positions (P{row['Start Position']} → P{row['Final Position']})")
                    else:
                        st.info("No significant position gainers in this race")
                
                with col2:
                    st.markdown("### 📉 Position Losses")
                    losers = changes_df[changes_df['Positions Gained'] < -1].head(5)
                    if not losers.empty:
                        for _, row in losers.iterrows():
                            name = row.get('Full Name', row['Driver'])
                            st.error(f"📉 **{name}**: {row['Positions Gained']} positions (P{row['Start Position']} → P{row['Final Position']})")
                    else:
                        st.info("No significant position losses in this race")
                
                # Full results table
                st.subheader("📋 Complete Position Changes")
                if 'Full Name' in changes_df.columns:
                    display_df = changes_df[['Full Name', 'Start Position', 'Final Position', 'Positions Gained']]
                    display_df = display_df.rename(columns={'Full Name': 'Driver'})  # Rename for clarity
                else:
                    display_df = changes_df
                st.dataframe(display_df, use_container_width=True)
                
                # Race insights
                try:
                    best_gainer = changes_df.loc[changes_df['Positions Gained'].idxmax()]
                    worst_loser = changes_df.loc[changes_df['Positions Gained'].idxmin()]
                    
                    st.subheader("🏆 Race Insights")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if best_gainer['Positions Gained'] > 0:
                            name = best_gainer.get('Full Name', best_gainer['Driver'])
                            st.success(f"**🏆 Race Hero**: {name} gained {best_gainer['Positions Gained']} positions!")
                        
                    with col2:
                        if worst_loser['Positions Gained'] < -1:
                            name = worst_loser.get('Full Name', worst_loser['Driver'])
                            st.error(f"**😔 Tough Day**: {name} lost {abs(worst_loser['Positions Gained'])} positions")
                            
                except:
                    pass
            else:
                st.warning("Could not calculate position changes")
                
        except Exception as e:
            st.error(f"Error creating position analysis: {e}")
            st.info("💡 Try a different race session")

def create_position_chart(position_df):
    """Create position tracking chart"""
    try:
        if position_df is None or position_df.empty:
            return None
        
        fig = go.Figure()
        
        # Get top drivers (those who finished in top 10 or had interesting position changes)
        final_positions = position_df.groupby('Driver')['Position'].last()
        
        # Show top 10 finishers + drivers with big position changes
        top_finishers = final_positions.sort_values().head(10).index.tolist()
        
        # Add drivers with significant position changes
        start_positions = position_df.groupby('Driver')['Position'].first()
        position_changes = start_positions - final_positions  # Positive = gained positions
        big_movers = position_changes[abs(position_changes) >= 3].index.tolist()
        
        # Combine and deduplicate
        drivers_to_show = list(set(top_finishers + big_movers))[:12]  # Limit to 12 for readability
        
        # Create traces for each driver
        colors = px.colors.qualitative.Set3
        
        for i, driver in enumerate(drivers_to_show):
            driver_data = position_df[position_df['Driver'] == driver].sort_values('LapNumber')
            
            if not driver_data.empty:
                color = colors[i % len(colors)]
                
                fig.add_trace(go.Scatter(
                    x=driver_data['LapNumber'],
                    y=driver_data['Position'],
                    mode='lines+markers',
                    name=driver,
                    line=dict(width=2, color=color),
                    marker=dict(size=4),
                    hovertemplate=f'<b>{driver}</b><br>Lap: %{{x}}<br>Position: %{{y}}<extra></extra>'
                ))
        
        # Update layout
        fig.update_layout(
            title="Race Position Changes Throughout the Race",
            xaxis_title="Lap Number",
            yaxis_title="Position",
            yaxis=dict(
                autorange='reversed',  # Position 1 at top
                dtick=1,  # Show every position
                range=[max(position_df['Position']) + 0.5, 0.5]  # Set range properly
            ),
            height=600,
            hovermode='x unified',
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02
            )
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating position chart: {e}")
        return None