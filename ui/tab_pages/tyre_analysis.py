"""
Tyre compound analysis tab.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from analysis_utils import format_lap_time


def render_tyre_analysis_tab(session):
    """Render tyre compound analysis tab."""
    st.header("Tyre Compound Analysis")

    if not hasattr(session, 'laps') or session.laps.empty:
        st.error("No lap data available for tyre analysis")
        return

    if 'Compound' not in session.laps.columns:
        st.warning("Tyre compound data not available for this session")
        return

    available_drivers = session.laps['Driver'].unique().tolist()
    if not available_drivers:
        st.warning("No drivers found in this session")
        return

    default_count = min(5, len(available_drivers))
    selected_drivers = st.multiselect(
        "Select drivers for tyre analysis (max 8):",
        available_drivers,
        default=available_drivers[:default_count],
        max_selections=8,
    )

    if not selected_drivers:
        st.warning("Please select at least one driver for tyre analysis")
        return

    try:
        with st.spinner("Analyzing tyre compound data..."):
            tyre_data = _analyze_tyre_compounds(session, selected_drivers)

        if not tyre_data:
            st.error("Could not analyze tyre compound data")
            return

        _render_compound_overview(tyre_data)
        st.markdown("---")
        _render_stint_analysis(selected_drivers, tyre_data)
        st.markdown("---")
        _render_compound_performance(tyre_data)
        st.markdown("---")
        _render_strategy_insights(tyre_data)
    except Exception as e:
        st.error(f"Error in tyre analysis: {e}")


# ── analysis helpers ────────────────────────────────────────────────────

_COMPOUND_COLORS = {
    'SOFT': '#FF0000',
    'MEDIUM': '#FFFF00',
    'HARD': '#FFFFFF',
    'INTERMEDIATE': '#00FF00',
    'WET': '#0000FF',
}


def _get_compound_color(compound: str) -> str:
    return _COMPOUND_COLORS.get(compound.upper(), '#808080')


_fmt_lap = format_lap_time


def _analyze_tyre_compounds(session, selected_drivers):
    tyre_analysis = {}
    for driver in selected_drivers:
        driver_laps = session.laps[session.laps['Driver'] == driver].copy()
        if driver_laps.empty:
            continue

        valid = driver_laps[
            (driver_laps['LapTime'].notna())
            & (driver_laps['Compound'].notna())
            & (driver_laps['LapTime'] > pd.Timedelta(seconds=30))
            & (driver_laps['LapTime'] < pd.Timedelta(seconds=200))
        ].copy()
        if valid.empty:
            continue

        valid['LapTimeSeconds'] = valid['LapTime'].dt.total_seconds()
        compounds = {}
        for compound in valid['Compound'].unique():
            cl = valid[valid['Compound'] == compound]
            compounds[compound] = {
                'lap_count': len(cl),
                'avg_pace': cl['LapTimeSeconds'].mean(),
                'best_lap': cl['LapTimeSeconds'].min(),
                'worst_lap': cl['LapTimeSeconds'].max(),
                'consistency': cl['LapTimeSeconds'].std(),
                'lap_numbers': cl['LapNumber'].tolist(),
                'lap_times': cl['LapTimeSeconds'].tolist(),
                'compound_color': _get_compound_color(compound),
            }
        if compounds:
            tyre_analysis[driver] = compounds
    return tyre_analysis


# ── rendering helpers ───────────────────────────────────────────────────

def _render_compound_overview(tyre_data):
    st.subheader("Compound Usage Overview")
    rows = []
    for driver, compounds in tyre_data.items():
        total = sum(d['lap_count'] for d in compounds.values())
        for compound, d in compounds.items():
            rows.append({
                'Driver': driver,
                'Compound': compound,
                'Laps Used': d['lap_count'],
                'Percentage': f"{d['lap_count'] / total * 100:.1f}%",
                'Avg Pace': _fmt_lap(d['avg_pace']),
                'Best Lap': _fmt_lap(d['best_lap']),
                'Consistency': f"{d['consistency']:.3f}s",
            })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)


def _render_stint_analysis(selected_drivers, tyre_data):
    st.subheader("Tyre Stint Visualization")
    fig = go.Figure()

    for driver in selected_drivers:
        if driver not in tyre_data:
            continue
        for compound, data in tyre_data[driver].items():
            laps = data['lap_numbers']
            if not laps:
                continue
            stints = _group_consecutive(laps)
            for stint in stints:
                start_lap, end_lap = min(stint), max(stint)
                duration = end_lap - start_lap + 1
                fig.add_trace(go.Bar(
                    x=[duration], y=[driver], base=[start_lap - 1],
                    orientation='h', name=f"{driver} - {compound}",
                    marker_color=data['compound_color'],
                    hovertemplate=(
                        f'<b>{driver}</b><br>Compound: {compound}<br>'
                        f'Laps: {start_lap}-{end_lap} ({duration} laps)<br>'
                        f'Avg Pace: {_fmt_lap(data["avg_pace"])}<extra></extra>'
                    ),
                    showlegend=False,
                ))

    fig.update_layout(
        title="Tyre Stint Timeline", xaxis_title="Lap Number",
        yaxis_title="Driver", height=400, barmode='stack',
    )
    st.plotly_chart(fig, use_container_width=True)


def _group_consecutive(numbers):
    stints, current = [], [numbers[0]]
    for i in range(1, len(numbers)):
        if numbers[i] == numbers[i - 1] + 1:
            current.append(numbers[i])
        else:
            stints.append(current)
            current = [numbers[i]]
    stints.append(current)
    return stints


def _render_compound_performance(tyre_data):
    st.subheader("Compound Performance Comparison")
    perf = {}
    for compounds in tyre_data.values():
        for compound, d in compounds.items():
            perf.setdefault(compound, {'paces': [], 'laps': [], 'color': d['compound_color']})
            perf[compound]['paces'].append(d['avg_pace'])
            perf[compound]['laps'].append(d['lap_count'])

    if not perf:
        return

    compounds = list(perf.keys())
    avg_paces = [sum(perf[c]['paces']) / len(perf[c]['paces']) for c in compounds]
    colors = [perf[c]['color'] for c in compounds]

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(go.Bar(
            x=compounds, y=avg_paces, marker_color=colors,
            text=[_fmt_lap(p) for p in avg_paces], textposition='auto',
        ))
        fig.update_layout(title="Average Pace by Compound", xaxis_title="Compound",
                          yaxis_title="Lap Time (seconds)", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        total_laps = [sum(perf[c]['laps']) for c in compounds]
        fig = go.Figure(go.Pie(labels=compounds, values=total_laps, marker_colors=colors))
        fig.update_layout(title="Compound Usage Distribution")
        st.plotly_chart(fig, use_container_width=True)


def _render_strategy_insights(tyre_data):
    st.subheader("Tyre Strategy Insights")
    all_paces = {}
    all_usage = {}
    for compounds in tyre_data.values():
        for compound, d in compounds.items():
            all_paces.setdefault(compound, []).append(d['avg_pace'])
            all_usage[compound] = all_usage.get(compound, 0) + d['lap_count']

    if not all_paces:
        return

    avg = {c: sum(p) / len(p) for c, p in all_paces.items()}
    fastest = min(avg, key=avg.get)
    slowest = max(avg, key=avg.get)

    c1, c2 = st.columns(2)
    with c1:
        st.success(f"**Fastest Compound**: {fastest} (avg: {_fmt_lap(avg[fastest])})")
        if len(avg) > 1:
            gap = avg[slowest] - avg[fastest]
            st.info(f"**Pace Gap**: {gap:.3f}s between fastest and slowest")
    with c2:
        most_used = max(all_usage, key=all_usage.get)
        st.info(f"**Most Used**: {most_used} ({all_usage[most_used]} laps)")
