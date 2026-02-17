"""
ML Test Page
Inspect and validate each stage of the F1 ML prediction pipeline.
"""

import os
import sys

# Ensure the repo root is on the path so all ml.* imports work when Streamlit
# runs this file from the pages/ sub-directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cache_config  # noqa: F401 — initialises FastF1 cache once

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional

from ml import MLState, MLConfig
from ml.pipeline import F1MLPipeline


# ─── Session-state helpers ────────────────────────────────────────────────────

_STATE_DEFAULTS = {
    "ml_pipeline": None,
    "ml_state_log": [],       # list[tuple[str, bool, str]]  (state, passed, msg)
    "ml_current_state": MLState.IDLE,
}


def _init_session_state() -> None:
    for key, val in _STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ─── Per-state validators ─────────────────────────────────────────────────────

def _validate_ingest(pipeline: F1MLPipeline) -> tuple[bool, str]:
    if pipeline.race_results is None or pipeline.race_results.empty:
        return False, "Race results not loaded or empty"
    n_rows = len(pipeline.race_results)
    n_races = (
        pipeline.race_results["EventName"].nunique()
        if "EventName" in pipeline.race_results.columns
        else "?"
    )
    return True, f"Loaded {n_rows:,} rows across {n_races} races"


def _validate_engineer(pipeline: F1MLPipeline) -> tuple[bool, str]:
    if pipeline.features is None or pipeline.features.empty:
        return False, "Features not created or empty"
    n_rows, n_cols = pipeline.features.shape
    return True, f"Engineered {n_cols} columns across {n_rows:,} rows"


def _validate_store(pipeline: F1MLPipeline) -> tuple[bool, str]:
    if pipeline.X_train is None:
        return False, "Training data not prepared"
    missing = [
        col for col in ("Abbreviation", "Year", "EventName", "RoundNumber")
        if col not in pipeline.X_train.columns
    ]
    if missing:
        return (
            False,
            "ELO metadata missing from X_train — "
            + ", ".join(f"'{c}'" for c in missing)
            + " (ELO bug not fixed)",
        )
    return (
        True,
        f"Train: {len(pipeline.X_train):,} rows, "
        f"Test: {len(pipeline.X_test):,} rows; "
        "all ELO metadata present",
    )


def _validate_elo(pipeline: F1MLPipeline) -> tuple[bool, str]:
    model = pipeline.models.get("ELO")
    if model is None:
        return False, "ELO model not trained"
    if not model.is_trained:
        return False, "ELO model is_trained flag is False"
    n_drivers = len(model.ratings)
    if n_drivers == 0:
        return (
            False,
            "No drivers tracked — 'Abbreviation' was missing from X_train",
        )
    rating_values = list(model.ratings.values())
    if len(set(rating_values)) == 1:
        return (
            False,
            f"All {n_drivers} drivers stuck at rating "
            f"{rating_values[0]:.0f} — ELO updates never ran",
        )
    lo, hi = min(rating_values), max(rating_values)
    return True, f"Tracking {n_drivers} drivers; rating spread [{lo:.0f}–{hi:.0f}]"


def _validate_evaluate(pipeline: F1MLPipeline) -> tuple[bool, str]:
    if not pipeline.models:
        return False, "No models to evaluate"
    if not pipeline.evaluator.results:
        return False, "Evaluator has no stored results"
    return True, f"Evaluated: {', '.join(pipeline.evaluator.results)}"


_VALIDATORS = {
    "INGEST": _validate_ingest,
    "ENGINEER": _validate_engineer,
    "STORE": _validate_store,
    "ELO": _validate_elo,
    "EVALUATE": _validate_evaluate,
}


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def _render_sidebar() -> dict:
    with st.sidebar:
        st.header("ML Pipeline Control")

        st.subheader("Data Range")
        year_range = st.slider(
            "Year range",
            min_value=MLConfig.MIN_YEAR,
            max_value=MLConfig.MAX_YEAR,
            value=(2024, 2024),
            step=1,
        )

        st.subheader("Run Mode")
        run_mode = st.radio(
            "Execution mode",
            options=["Run All States", "Individual State"],
            index=0,
        )

        individual_state: Optional[str] = None
        if run_mode == "Individual State":
            individual_state = st.selectbox(
                "Select state",
                options=["INGEST", "ENGINEER", "STORE", "ELO", "EVALUATE"],
            )

        st.subheader("Feature Store")
        feature_name = st.text_input("Feature set name", value="f1_features")

        st.subheader("Pipeline Status")
        current_state: MLState = st.session_state.get(
            "ml_current_state", MLState.IDLE
        )
        st.info(f"State: **{current_state.value.upper()}**")

        run_button = st.button(
            "Run Pipeline", type="primary", use_container_width=True
        )

        if st.button("Reset Pipeline", use_container_width=True):
            for key, val in _STATE_DEFAULTS.items():
                st.session_state[key] = val if not isinstance(val, list) else []
            st.rerun()

    return {
        "year_range": year_range,
        "run_mode": run_mode,
        "individual_state": individual_state,
        "feature_name": feature_name or "f1_features",
        "run_button": run_button,
    }


# ─── Pipeline execution ───────────────────────────────────────────────────────

def _run_pipeline(config: dict) -> None:
    min_year, max_year = config["year_range"]
    years = list(range(min_year, max_year + 1))
    feature_name = config["feature_name"]

    pipeline = F1MLPipeline(min_year=min_year, max_year=max_year)
    st.session_state["ml_pipeline"] = pipeline
    st.session_state["ml_state_log"] = []
    log = st.session_state["ml_state_log"]

    def _run(label: str, fn, *args) -> bool:
        with st.spinner(f"Running {label}…"):
            ok = fn(*args)
        log.append((label, ok))
        return ok

    if config["run_mode"] == "Run All States":
        if not _run("INGEST", pipeline.run_ingest_state, years):
            return
        if not _run("ENGINEER", pipeline.run_engineer_state):
            return
        if not _run("STORE", pipeline.run_store_state, feature_name):
            return
        if not _run("ELO", pipeline.run_elo_model_state):
            return
        _run("EVALUATE", pipeline.run_evaluate_state)
    else:
        state = config["individual_state"]
        dispatch = {
            "INGEST": (pipeline.run_ingest_state, [years]),
            "ENGINEER": (pipeline.run_engineer_state, []),
            "STORE": (pipeline.run_store_state, [feature_name]),
            "ELO": (pipeline.run_elo_model_state, []),
            "EVALUATE": (pipeline.run_evaluate_state, []),
        }
        fn, args = dispatch[state]
        _run(state, fn, *args)

    st.session_state["ml_current_state"] = pipeline.state


# ─── Results display ──────────────────────────────────────────────────────────

def _render_state_diagnostics(pipeline: F1MLPipeline) -> None:
    st.subheader("State Diagnostics")
    all_passed = True

    for state_name, validator in _VALIDATORS.items():
        try:
            passed, msg = validator(pipeline)
        except Exception as exc:
            passed, msg = False, f"Validator error: {exc}"

        icon = "✅" if passed else "❌"
        if not passed:
            all_passed = False

        with st.expander(f"{icon} {state_name}", expanded=not passed):
            if passed:
                st.success(msg)
            else:
                st.error(msg)

    if all_passed:
        st.success("All states passed validation.")


def _render_elo_rankings(pipeline: F1MLPipeline) -> None:
    elo = pipeline.models.get("ELO")
    if elo is None or not elo.is_trained or not elo.ratings:
        return

    st.subheader("ELO Driver Rankings")
    rankings = elo.get_current_rankings()
    st.dataframe(rankings, use_container_width=True, height=420)


def _render_evaluation(pipeline: F1MLPipeline) -> None:
    if not pipeline.evaluator.results:
        return

    st.subheader("Model Evaluation")
    try:
        comparison = pipeline.evaluator.compare_models()
        st.dataframe(comparison, use_container_width=True)
    except Exception:
        st.json(
            {
                model: {m: round(float(v), 4) for m, v in metrics.items()}
                for model, metrics in pipeline.evaluator.results.items()
            }
        )


def _render_feature_info(pipeline: F1MLPipeline) -> None:
    if pipeline.features is None or pipeline.features.empty:
        return

    with st.expander("Feature Set Info"):
        n_rows, n_cols = pipeline.features.shape
        st.write(f"**Shape:** {n_rows:,} rows × {n_cols} columns")
        st.write(f"**Columns:** {list(pipeline.features.columns)}")
        st.dataframe(pipeline.features.head(10), use_container_width=True)


def _render_results(pipeline: Optional[F1MLPipeline]) -> None:
    if pipeline is None:
        st.info(
            "No results yet. Configure the pipeline in the sidebar and click "
            "**Run Pipeline**."
        )
        return

    _render_state_diagnostics(pipeline)
    _render_elo_rankings(pipeline)
    _render_evaluation(pipeline)
    _render_feature_info(pipeline)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    st.title("ML Pipeline Test Page")
    st.caption(
        "Configure, run, and validate each stage of the F1 ML prediction "
        "pipeline. State diagnostics flag bugs (e.g. the ELO metadata bug) "
        "automatically."
    )

    _init_session_state()

    config = _render_sidebar()

    if config["run_button"]:
        _run_pipeline(config)
        st.rerun()

    _render_results(st.session_state.get("ml_pipeline"))


if __name__ == "__main__":
    main()
