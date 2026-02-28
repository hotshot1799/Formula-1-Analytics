"""
Race position tracking tab.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from analysis_utils import get_position_data_safe, calculate_position_changes
from data_loader import load_session
from team_colors import get_driver_color, initialize_session_colors


def render_position_tracking_tab(session):
    """Render position tracking tab."""
    st.header("Race Position Tracking")

    session_type = st.session_state.get('session_type', 'Unknown')

    if session_type != 'R':
        st.info("Position tracking is only available for race sessions")
        if st.button("Load Race Session Instead"):
            with st.spinner("Loading race data..."):
                race_session = load_session(
                    st.session_state.year, st.session_state.event, 'R'
                )
                if race_session and hasattr(race_session, 'laps') and not race_session.laps.empty:
                    st.session_state.session = race_session
                    st.session_state.session_type = 'R'
                    st.session_state.event_info = (
                        f"{st.session_state.event} R ({st.session_state.year})"
                    )
                    st.rerun()
                else:
                    st.error("No race data available for this event.")
        return

    try:
        _render_race_positions(session)
    except Exception as e:
        st.error(f"Error creating position analysis: {e}")


def _render_race_positions(session):
    """Core position-tracking logic (may raise)."""
    with st.spinner("Analyzing race positions..."):
        position_df = get_position_data_safe(session)

    if position_df is None or position_df.empty:
        st.warning("No position data available for this race")
        return

    st.success(f"Position data loaded: {len(position_df)} position records")

    if 'driver_colors' not in st.session_state:
        initialize_session_colors(session)

    fig = create_position_chart(position_df, session)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    result = calculate_position_changes(position_df, session)
    for warning in result.get("warnings", []):
        st.info(warning)
    changes_df = result.get("data")
    if changes_df is None or changes_df.empty:
        st.warning("Could not calculate position changes")
        return

    st.subheader("Position Changes Summary")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Biggest Gainers")
        gainers = changes_df[changes_df['Positions Gained'] > 0].head(5)
        if not gainers.empty:
            for _, row in gainers.iterrows():
                name = _display_name(row)
                st.success(
                    f"**{name}**: +{row['Positions Gained']} positions "
                    f"(P{row['Start Position']} -> P{row['Final Position']})"
                )
        else:
            st.info("No significant position gainers in this race")

    with col2:
        st.markdown("### Position Losses")
        losers = changes_df[changes_df['Positions Gained'] < -1].head(5)
        if not losers.empty:
            for _, row in losers.iterrows():
                name = _display_name(row)
                st.error(
                    f"**{name}**: {row['Positions Gained']} positions "
                    f"(P{row['Start Position']} -> P{row['Final Position']})"
                )
        else:
            st.info("No significant position losses in this race")

    st.subheader("Complete Position Changes")
    display_df = changes_df.copy()
    if 'Full Name' in display_df.columns:
        display_df['Display Name'] = display_df.apply(
            lambda r: r['Full Name']
            if pd.notna(r.get('Full Name')) and r['Full Name'] != r['Driver']
            else r['Driver'],
            axis=1,
        )
    else:
        display_df['Display Name'] = display_df['Driver']
    final_df = display_df[
        ['Display Name', 'Start Position', 'Final Position', 'Positions Gained']
    ].copy()
    final_df.columns = ['Driver', 'Start Position', 'Final Position', 'Positions Gained']
    st.dataframe(final_df, use_container_width=True)


def _display_name(row) -> str:
    if 'Full Name' in row and pd.notna(row.get('Full Name')) and row['Full Name'] != row['Driver']:
        return row['Full Name']
    return row['Driver']


def create_position_chart(position_df, session):
    """Create position tracking chart with proper driver names."""
    if position_df is None or position_df.empty:
        return None

    fig = go.Figure()

    final_positions = position_df.groupby('Driver')['Position'].last()
    top_finishers = final_positions.sort_values().head(10).index.tolist()

    start_positions = position_df.groupby('Driver')['Position'].first()
    position_changes = start_positions - final_positions
    big_movers = position_changes[abs(position_changes) >= 3].index.tolist()

    drivers_to_show = list(set(top_finishers + big_movers))[:12]

    for driver in drivers_to_show:
        driver_data = position_df[position_df['Driver'] == driver].sort_values('LapNumber')
        if not driver_data.empty:
            color = get_driver_color(driver, session)
            fig.add_trace(go.Scatter(
                x=driver_data['LapNumber'],
                y=driver_data['Position'],
                mode='lines+markers',
                name=driver,
                line=dict(width=3, color=color),
                marker=dict(size=5, color=color),
                hovertemplate=(
                    f'<b>{driver}</b><br>'
                    'Lap: %{x}<br>Position: %{y}<extra></extra>'
                ),
            ))

    fig.update_layout(
        title="Race Position Changes Throughout the Race",
        xaxis_title="Lap Number",
        yaxis_title="Position",
        yaxis=dict(
            autorange='reversed',
            dtick=1,
            range=[max(position_df['Position']) + 0.5, 0.5],
        ),
        height=600,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
    )
    return fig
