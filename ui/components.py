"""
Shared UI components used across the F1 Analytics dashboard.

Consolidates podium display, qualifying results, and fastest-times
rendering that was previously duplicated in welcome.py and
position_tracking.py.
"""
import streamlit as st
import pandas as pd


def render_podium(drivers: list[str]) -> None:
    """Display a gold/silver/bronze podium for up to 3 drivers.

    Args:
        drivers: Ordered list of driver names/codes (1st, 2nd, 3rd).
    """
    col1, col2, col3 = st.columns(3)
    labels = [
        ("1st WINNER", "success"),
        ("2nd SECOND", "info"),
        ("3rd THIRD", "warning"),
    ]
    cols = [col1, col2, col3]
    for i, (col, (label, style)) in enumerate(zip(cols, labels)):
        if i < len(drivers):
            with col:
                getattr(st, style)(f"**{label}**\n### {drivers[i]}")


def render_qualifying_results(session) -> None:
    """Extract fastest laps from a qualifying session and display top-3
    plus a full results table.
    """
    fastest_laps = _collect_fastest_laps(session)
    if not fastest_laps:
        return

    df = pd.DataFrame(fastest_laps).sort_values("Seconds").head(10)
    df["Position"] = range(1, len(df) + 1)

    col1, col2, col3 = st.columns(3)
    labels = [
        ("1st POLE POSITION", "success"),
        ("2nd FRONT ROW", "info"),
        ("3rd THIRD", "warning"),
    ]
    cols = [col1, col2, col3]
    for i, (col, (label, style)) in enumerate(zip(cols, labels)):
        if i < len(df):
            with col:
                row = df.iloc[i]
                getattr(st, style)(
                    f"**{label}**\n### {row['Driver']}\n**{row['Time']}**"
                )

    st.markdown("### Complete Qualifying Results")
    display_df = df[["Position", "Driver", "Time"]].reset_index(drop=True)
    st.dataframe(display_df, use_container_width=True, height=350)


def render_fastest_times(session, count: int = 5) -> None:
    """Display fastest lap times for practice/other sessions."""
    fastest_laps = _collect_fastest_laps(session)
    if not fastest_laps:
        return

    df = pd.DataFrame(fastest_laps).sort_values("Seconds").head(count)

    st.markdown("### Fastest Times")
    for idx, (_, row) in enumerate(df.iterrows()):
        if idx == 0:
            st.success(f"**P1**: {row['Driver']} - {row['Time']}")
        else:
            st.info(f"**P{idx + 1}**: {row['Driver']} - {row['Time']}")


def render_session_results_table(dataframe: pd.DataFrame) -> None:
    """Render a generic session results table."""
    st.dataframe(dataframe, use_container_width=True)


# ── helpers ─────────────────────────────────────────────────────────────


def _collect_fastest_laps(session) -> list[dict]:
    """Return a list of dicts with Driver/Time/Seconds for each driver's
    fastest lap in the given session."""
    fastest_laps: list[dict] = []
    try:
        for driver in session.laps["Driver"].unique():
            try:
                fastest_lap = session.laps.pick_driver(driver).pick_fastest()
                total_seconds = fastest_lap["LapTime"].total_seconds()
                minutes = int(total_seconds // 60)
                seconds = total_seconds % 60
                fastest_laps.append(
                    {
                        "Driver": driver,
                        "Time": f"{minutes}:{seconds:06.3f}",
                        "Seconds": total_seconds,
                    }
                )
            except Exception:
                continue
    except Exception:
        pass
    return fastest_laps
