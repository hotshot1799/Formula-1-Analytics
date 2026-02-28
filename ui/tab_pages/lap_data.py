"""
Lap-level data: lap time analysis and data export.

Merged from the former lap_analysis.py and data_export.py.
"""
import streamlit as st
import pandas as pd
from chart_creators import create_lap_times_chart
from analysis_utils import calculate_lap_statistics, prepare_export_data


# ── Lap Analysis ────────────────────────────────────────────────────────

def render_lap_analysis_tab(session):
    """Render lap analysis tab."""
    st.header("Lap Time Analysis")

    all_drivers = session.laps['Driver'].unique().tolist()
    default_count = min(5, len(all_drivers))
    selected_drivers = st.multiselect(
        "Select drivers (max 10):",
        all_drivers,
        default=all_drivers[:default_count],
        max_selections=10,
    )

    if not selected_drivers:
        st.warning("Select at least one driver")
        return

    try:
        with st.spinner("Creating analysis..."):
            fig = create_lap_times_chart(session, selected_drivers)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Statistics")
        lap_stats_df = calculate_lap_statistics(session, selected_drivers)
        if lap_stats_df is not None:
            st.dataframe(lap_stats_df, use_container_width=True)
        else:
            st.warning("No statistics available")
    except Exception as e:
        st.error(f"Error in lap analysis: {e}")


# ── Data Export ─────────────────────────────────────────────────────────

def render_data_export_tab(session):
    """Render data export tab."""
    st.header("Data Export & Download")

    try:
        _render_export(session)
    except Exception as e:
        st.error(f"Error preparing data for export: {e}")


def _render_export(session):
    st.subheader("Session Data Overview")
    total_laps = len(session.laps)
    total_drivers = len(session.laps['Driver'].unique())
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Laps", total_laps)
    with c2:
        st.metric("Drivers", total_drivers)
    with c3:
        st.metric("Data Points", total_laps * total_drivers)

    lap_data = prepare_export_data(session)
    if lap_data is None or lap_data.empty:
        st.error("No data available for export")
        return

    st.subheader("Data Preview")
    st.dataframe(lap_data.head(10), use_container_width=True)

    st.subheader("Download Options")
    c1, c2 = st.columns(2)

    with c1:
        csv_data = lap_data.to_csv(index=False)
        filename = f"{st.session_state.event_info.replace(' ', '_')}_complete_data.csv"
        st.download_button(
            label="Download Complete Dataset",
            data=csv_data,
            file_name=filename,
            mime='text/csv',
            use_container_width=True,
        )
        file_size = len(csv_data.encode('utf-8')) / 1024
        st.info(f"**File size:** {file_size:.1f} KB")

    with c2:
        summary_data = []
        for driver in lap_data['Driver'].unique():
            driver_laps = lap_data[lap_data['Driver'] == driver]
            valid_laps = driver_laps[driver_laps['LapTime'] != 'N/A']
            summary_data.append({
                'Driver': driver,
                'Total_Laps': len(driver_laps),
                'Valid_Laps': len(valid_laps),
                'Best_Lap': valid_laps['LapTime'].iloc[0] if not valid_laps.empty else 'N/A',
                'Final_Position': (
                    driver_laps['Position'].iloc[-1]
                    if 'Position' in driver_laps.columns
                    else 'N/A'
                ),
            })
        summary_df = pd.DataFrame(summary_data)
        csv_summary = summary_df.to_csv(index=False)
        summary_filename = f"{st.session_state.event_info.replace(' ', '_')}_summary.csv"
        st.download_button(
            label="Download Driver Summary",
            data=csv_summary,
            file_name=summary_filename,
            mime='text/csv',
            use_container_width=True,
        )
        st.dataframe(summary_df.head(5), use_container_width=True)
