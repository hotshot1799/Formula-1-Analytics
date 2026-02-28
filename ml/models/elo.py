"""
ELO Rating Model for F1 Driver Rankings
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

from ml.models.base import BaseF1Model
from ml import MLConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ELOModel(BaseF1Model):
    """
    ELO-based ranking system for F1 drivers
    Updates ratings based on race results
    """

    required_columns = ['Abbreviation', 'Year', 'EventName', 'RoundNumber']

    def __init__(
        self,
        k_factor: int = None,
        initial_rating: int = None
    ):
        """
        Initialize ELO model

        Args:
            k_factor: ELO K-factor (sensitivity to updates)
            initial_rating: Starting rating for new drivers
        """
        super().__init__("ELO")
        self.k_factor = k_factor or MLConfig.ELO_K_FACTOR
        self.initial_rating = initial_rating or MLConfig.ELO_INITIAL_RATING
        self.ratings: Dict[str, float] = {}
        self.rating_history: Dict[str, list] = {}

    def _get_rating(self, driver: str) -> float:
        """
        Get current rating for a driver

        Args:
            driver: Driver abbreviation

        Returns:
            Current ELO rating
        """
        if driver not in self.ratings:
            self.ratings[driver] = self.initial_rating
            self.rating_history[driver] = [self.initial_rating]

        return self.ratings[driver]

    def _expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        Calculate expected score for driver A against driver B

        Args:
            rating_a: Rating of driver A
            rating_b: Rating of driver B

        Returns:
            Expected score (0 to 1)
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def _update_ratings(
        self,
        driver: str,
        opponent: str,
        actual_score: float
    ) -> None:
        """
        Update ELO ratings after a race

        Args:
            driver: Driver being updated
            opponent: Opponent driver
            actual_score: Actual score (1 for win, 0 for loss, 0.5 for tie)
        """
        driver_rating = self._get_rating(driver)
        opponent_rating = self._get_rating(opponent)

        expected = self._expected_score(driver_rating, opponent_rating)

        new_rating = driver_rating + self.k_factor * (actual_score - expected)

        self.ratings[driver] = new_rating
        self.rating_history[driver].append(new_rating)

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """
        Train ELO model on race results

        Args:
            X: Feature DataFrame with race information (must include
               Abbreviation, Year, EventName, and RoundNumber columns)
            y: Race positions (target)
        """
        for col in self.required_columns:
            if col not in X.columns:
                raise ValueError(
                    f"ELO model requires '{col}' column in input data. "
                    "Use model.prepare_input(X, meta) to merge identifier "
                    "columns before calling train()."
                )

        logger.info("Training ELO model...")

        data = X.copy()
        data['Position'] = y

        data_sorted = data.sort_values(['Year', 'RoundNumber'])

        for _, race_group in data_sorted.groupby(['Year', 'EventName']):
            race_results = race_group.sort_values('Position')

            drivers = race_results['Abbreviation'].values

            for i, driver_a in enumerate(drivers):
                for driver_b in drivers[i+1:]:
                    self._update_ratings(driver_a, driver_b, 1.0)
                    self._update_ratings(driver_b, driver_a, 0.0)

        self.is_trained = True
        logger.info(f"ELO model trained. Tracking {len(self.ratings)} drivers")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict race positions based on current ELO ratings

        Args:
            X: Feature DataFrame (must include Abbreviation, Year,
               EventName, RoundNumber)

        Returns:
            Predicted positions
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        for col in self.required_columns:
            if col not in X.columns:
                raise ValueError(
                    f"ELO model requires '{col}' column in input data."
                )

        predictions = []

        for _, race_group in X.groupby(['Year', 'EventName']):
            drivers = race_group['Abbreviation'].values

            driver_ratings = [(driver, self._get_rating(driver)) for driver in drivers]

            driver_ratings.sort(key=lambda x: x[1], reverse=True)

            position_map = {driver: idx + 1 for idx, (driver, _) in enumerate(driver_ratings)}

            race_predictions = [position_map.get(driver, 20) for driver in drivers]
            predictions.extend(race_predictions)

        return np.array(predictions)

    def get_current_rankings(self) -> pd.DataFrame:
        """
        Get current driver rankings

        Returns:
            DataFrame with driver rankings
        """
        rankings = pd.DataFrame([
            {'Driver': driver, 'Rating': rating}
            for driver, rating in self.ratings.items()
        ])

        rankings = rankings.sort_values('Rating', ascending=False)
        rankings['Rank'] = range(1, len(rankings) + 1)

        return rankings

    def get_rating_history(self, driver: str) -> Optional[list]:
        """
        Get rating history for a driver

        Args:
            driver: Driver abbreviation

        Returns:
            List of historical ratings
        """
        return self.rating_history.get(driver)

    def predict_head_to_head(self, driver_a: str, driver_b: str) -> Dict[str, float]:
        """
        Predict head-to-head outcome between two drivers

        Args:
            driver_a: First driver
            driver_b: Second driver

        Returns:
            Dictionary with win probabilities
        """
        rating_a = self._get_rating(driver_a)
        rating_b = self._get_rating(driver_b)

        prob_a_wins = self._expected_score(rating_a, rating_b)
        prob_b_wins = 1 - prob_a_wins

        return {
            f'{driver_a}_win_prob': prob_a_wins,
            f'{driver_b}_win_prob': prob_b_wins,
            f'{driver_a}_rating': rating_a,
            f'{driver_b}_rating': rating_b
        }


if __name__ == "__main__":
    sample_data = pd.DataFrame({
        'Year': [2024] * 6,
        'EventName': ['Bahrain'] * 3 + ['Saudi Arabia'] * 3,
        'RoundNumber': [1] * 3 + [2] * 3,
        'Abbreviation': ['VER', 'LEC', 'SAI'] * 2,
    })
    sample_positions = pd.Series([1, 2, 3, 2, 1, 3])

    elo = ELOModel()
    elo.train(sample_data, sample_positions)

    rankings = elo.get_current_rankings()
    print("\nCurrent Rankings:")
    print(rankings)

    predictions = elo.predict(sample_data)
    print(f"\nPredictions: {predictions}")
