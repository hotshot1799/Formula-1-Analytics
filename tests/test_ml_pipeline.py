"""
Unit tests for the F1 ML pipeline.

These tests use small synthetic dataframes so they run in seconds
without needing a network connection or the FastF1 API.
"""

import pytest
import pandas as pd
import numpy as np

from ml.feature_store import FeatureStore
from ml.feature_engine import FeatureEngineer
from ml.models.elo import ELOModel
from ml.models.base import BaseF1Model


# ── helpers ─────────────────────────────────────────────────────────────

def _make_race_results(n_races=4, drivers=("VER", "LEC", "HAM")):
    """Create a minimal race-results DataFrame."""
    rows = []
    for r in range(1, n_races + 1):
        for pos, drv in enumerate(drivers, start=1):
            rows.append({
                "Year": 2024,
                "RoundNumber": r,
                "EventName": f"GP{r}",
                "Abbreviation": drv,
                "TeamName": {"VER": "Red Bull", "LEC": "Ferrari", "HAM": "Mercedes"}[drv],
                "Position": pos,
                "Points": max(0, 26 - pos * 3),
                "Status": "Finished",
                "GridPosition": pos,
                "FullName": drv,
                "DriverNumber": str(pos),
                "Country": "XX",
            })
    return pd.DataFrame(rows)


def _make_qual_results(race_df):
    """Mirror race results as qualifying results."""
    qual = race_df[["Year", "EventName", "Abbreviation", "Position"]].copy()
    return qual


# ── FeatureStore tests ──────────────────────────────────────────────────

class TestFeatureStore:
    def setup_method(self):
        self.store = FeatureStore()
        self.race = _make_race_results()

    def test_prepare_training_data_shapes(self):
        X_train, X_test, y_train, y_test, meta_train, meta_test = (
            self.store.prepare_training_data(self.race, test_size=0.25)
        )
        total = len(X_train) + len(X_test)
        assert total > 0
        assert len(X_train) == len(y_train)
        assert len(X_test) == len(y_test)
        assert len(meta_train) == len(X_train)
        assert len(meta_test) == len(X_test)

    def test_meta_has_identifier_columns(self):
        _, _, _, _, meta_train, meta_test = (
            self.store.prepare_training_data(self.race)
        )
        for col in ("Abbreviation", "Year", "EventName", "RoundNumber"):
            assert col in meta_train.columns, f"meta_train missing {col}"
            assert col in meta_test.columns, f"meta_test missing {col}"

    def test_identifier_cols_excluded_from_X(self):
        X_train, _, _, _, _, _ = self.store.prepare_training_data(self.race)
        for col in ("Abbreviation", "Year", "EventName", "RoundNumber"):
            assert col not in X_train.columns, f"{col} should not be in X_train"

    def test_index_alignment_after_dropna(self):
        df = self.race.copy()
        # Introduce a gap that dropna will create
        df.loc[1, "Position"] = np.nan
        X_train, X_test, _, _, meta_train, meta_test = (
            self.store.prepare_training_data(df)
        )
        # X and meta must share the same index so pd.concat aligns correctly
        assert list(X_train.index) == list(meta_train.index)
        assert list(X_test.index) == list(meta_test.index)
        # The full parent index should be contiguous (from reset_index)
        train_idx = list(X_train.index)
        assert train_idx == list(range(train_idx[0], train_idx[0] + len(train_idx)))


# ── ELOModel tests ──────────────────────────────────────────────────────

class TestELOModel:
    def setup_method(self):
        self.model = ELOModel()
        self.data = pd.DataFrame({
            "Year": [2024] * 6,
            "EventName": ["Bahrain"] * 3 + ["Saudi"] * 3,
            "RoundNumber": [1] * 3 + [2] * 3,
            "Abbreviation": ["VER", "LEC", "HAM", "VER", "HAM", "LEC"],
        })
        self.positions = pd.Series([1, 2, 3, 1, 2, 3])

    def test_train_and_predict(self):
        self.model.train(self.data, self.positions)
        assert self.model.is_trained
        assert len(self.model.ratings) == 3

        preds = self.model.predict(self.data)
        assert len(preds) == len(self.data)

    def test_ratings_diverge(self):
        self.model.train(self.data, self.positions)
        rating_values = list(self.model.ratings.values())
        assert len(set(rating_values)) > 1, "Ratings should not all be identical"

    def test_rankings_order(self):
        self.model.train(self.data, self.positions)
        rankings = self.model.get_current_rankings()
        assert rankings.iloc[0]["Driver"] == "VER"

    def test_missing_abbreviation_raises(self):
        bad_data = self.data.drop(columns=["Abbreviation"])
        with pytest.raises(ValueError, match="Abbreviation"):
            self.model.train(bad_data, self.positions)

    def test_missing_roundnumber_raises(self):
        bad_data = self.data.drop(columns=["RoundNumber"])
        with pytest.raises(ValueError, match="RoundNumber"):
            self.model.train(bad_data, self.positions)

    def test_predict_before_train_raises(self):
        with pytest.raises(ValueError, match="trained"):
            self.model.predict(self.data)


# ── BaseF1Model.prepare_input tests ─────────────────────────────────────

class TestPrepareInput:
    def test_returns_x_when_no_required_columns(self):
        """A model with no required_columns gets X back unchanged."""

        class PlainModel(BaseF1Model):
            required_columns = []

            def train(self, X, y):
                pass

            def predict(self, X):
                return np.zeros(len(X))

        m = PlainModel("plain")
        X = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = m.prepare_input(X)
        assert list(result.columns) == ["a", "b"]

    def test_merges_from_meta(self):
        elo = ELOModel()
        X = pd.DataFrame({"feat1": [10, 20]})
        meta = pd.DataFrame({
            "Abbreviation": ["VER", "HAM"],
            "Year": [2024, 2024],
            "EventName": ["GP1", "GP1"],
            "RoundNumber": [1, 1],
        })
        combined = elo.prepare_input(X, meta)
        assert "Abbreviation" in combined.columns
        assert "RoundNumber" in combined.columns
        assert len(combined) == 2

    def test_noop_when_already_present(self):
        elo = ELOModel()
        X = pd.DataFrame({
            "feat1": [10],
            "Abbreviation": ["VER"],
            "Year": [2024],
            "EventName": ["GP1"],
            "RoundNumber": [1],
        })
        result = elo.prepare_input(X)
        assert list(result.columns) == list(X.columns)

    def test_raises_when_meta_missing(self):
        elo = ELOModel()
        X = pd.DataFrame({"feat1": [10]})
        with pytest.raises(ValueError, match="meta is empty"):
            elo.prepare_input(X, meta=None)


# ── FeatureEngineer tests ──────────────────────────────────────────────

class TestFeatureEngineer:
    def test_no_duplicate_rows(self):
        race = _make_race_results(n_races=6)
        qual = _make_qual_results(race)
        eng = FeatureEngineer()
        features = eng.engineer_all_features(race, qual)

        dupes = features.duplicated(subset=["Year", "RoundNumber", "Abbreviation"])
        assert not dupes.any(), "Feature engineering produced duplicate rows"

    def test_row_count_preserved(self):
        race = _make_race_results(n_races=4, drivers=("VER", "LEC"))
        qual = _make_qual_results(race)
        eng = FeatureEngineer()
        features = eng.engineer_all_features(race, qual)

        assert len(features) == len(race)

    def test_team_features_dont_inflate_rows(self):
        race = _make_race_results(n_races=4)
        eng = FeatureEngineer()
        result = eng.create_team_features(race)
        assert len(result) == len(race)


# ── End-to-end: prepare_training_data → ELO train → ELO predict ────────

class TestEndToEnd:
    def test_full_flow(self):
        race = _make_race_results(n_races=10)
        qual = _make_qual_results(race)

        eng = FeatureEngineer()
        features = eng.engineer_all_features(race, qual)

        store = FeatureStore()
        X_train, X_test, y_train, y_test, meta_train, meta_test = (
            store.prepare_training_data(features, test_size=0.2)
        )

        elo = ELOModel()
        elo_input = elo.prepare_input(X_train, meta_train)
        elo.train(elo_input, y_train)

        elo_test_input = elo.prepare_input(X_test, meta_test)
        preds = elo.predict(elo_test_input)

        assert len(preds) == len(y_test)
        assert elo.is_trained
        assert len(elo.ratings) > 0
