"""
Feature Engineering Module (ENGINEER State)
Creates features from raw F1 data for ML models
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import logging

from ml import MLConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Generates ML features from F1 race data"""

    def __init__(self, window_size: int = None):
        """
        Initialize feature engineer

        Args:
            window_size: Number of races to look back for rolling features
        """
        self.window_size = window_size or MLConfig.FEATURE_WINDOW_RACES

    def create_driver_form_features(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create driver form features (recent performance)

        Args:
            results_df: Race results DataFrame

        Returns:
            DataFrame with form features
        """
        logger.info("Creating driver form features...")

        results_sorted = results_df.sort_values(['Year', 'RoundNumber'])

        features = []

        for driver in results_sorted['Abbreviation'].unique():
            driver_data = results_sorted[results_sorted['Abbreviation'] == driver].copy()

            driver_data['AvgPosition_Last3'] = (
                driver_data['Position']
                .rolling(window=3, min_periods=1)
                .mean()
            )

            driver_data['AvgPosition_Last5'] = (
                driver_data['Position']
                .rolling(window=5, min_periods=1)
                .mean()
            )

            driver_data['Points_Last3'] = (
                driver_data['Points']
                .rolling(window=3, min_periods=1)
                .sum()
            )

            driver_data['Points_Last5'] = (
                driver_data['Points']
                .rolling(window=5, min_periods=1)
                .sum()
            )

            driver_data['FinishRate_Last5'] = (
                driver_data['Status']
                .apply(lambda x: 1 if 'Finished' in str(x) or '+' in str(x) else 0)
                .rolling(window=5, min_periods=1)
                .mean()
            )

            driver_data['Podiums_Last5'] = (
                driver_data['Position']
                .apply(lambda x: 1 if x <= 3 else 0)
                .rolling(window=5, min_periods=1)
                .sum()
            )

            features.append(driver_data)

        result = pd.concat(features, ignore_index=True)
        logger.info(f"Created form features for {len(result)} records")

        return result

    def create_qualifying_features(
        self,
        race_df: pd.DataFrame,
        qual_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge qualifying features with race data

        Args:
            race_df: Race results
            qual_df: Qualifying results

        Returns:
            DataFrame with qualifying features added
        """
        logger.info("Creating qualifying features...")

        qual_features = qual_df[['Year', 'EventName', 'Abbreviation', 'Position']].copy()
        qual_features.rename(columns={'Position': 'QualifyingPosition'}, inplace=True)

        merged = race_df.merge(
            qual_features,
            on=['Year', 'EventName', 'Abbreviation'],
            how='left'
        )

        merged['QualifyingPosition'] = merged['QualifyingPosition'].fillna(20)

        merged['Grid_vs_Quali_Delta'] = (
            merged.get('GridPosition', merged['QualifyingPosition']) -
            merged['QualifyingPosition']
        )

        logger.info(f"Added qualifying features to {len(merged)} records")

        return merged

    def create_team_features(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create team-level features

        Args:
            results_df: Race results

        Returns:
            DataFrame with team features
        """
        logger.info("Creating team features...")

        results_sorted = results_df.sort_values(['Year', 'RoundNumber'])

        team_features = []

        for team in results_sorted['TeamName'].unique():
            team_data = results_sorted[results_sorted['TeamName'] == team].copy()

            team_data['Team_AvgPosition_Last3'] = (
                team_data['Position']
                .rolling(window=3, min_periods=1)
                .mean()
            )

            team_data['Team_Points_Last3'] = (
                team_data['Points']
                .rolling(window=3, min_periods=1)
                .sum()
            )

            team_data['Team_FinishRate_Last5'] = (
                team_data['Status']
                .apply(lambda x: 1 if 'Finished' in str(x) or '+' in str(x) else 0)
                .rolling(window=5, min_periods=1)
                .mean()
            )

            team_features.append(team_data)

        result = pd.concat(team_features, ignore_index=True)
        logger.info(f"Created team features for {len(result)} records")

        return result

    def create_track_history_features(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create features based on driver/team performance at specific tracks

        Args:
            results_df: Race results

        Returns:
            DataFrame with track history features
        """
        logger.info("Creating track history features...")

        results_sorted = results_df.sort_values(['Year', 'RoundNumber'])

        track_features = []

        for driver in results_sorted['Abbreviation'].unique():
            driver_data = results_sorted[results_sorted['Abbreviation'] == driver].copy()

            for track in driver_data['EventName'].unique():
                track_data = driver_data[driver_data['EventName'] == track].copy()

                track_data['Driver_Track_AvgPosition'] = (
                    track_data['Position']
                    .expanding(min_periods=1)
                    .mean()
                    .shift(1)
                )

                track_data['Driver_Track_BestPosition'] = (
                    track_data['Position']
                    .expanding(min_periods=1)
                    .min()
                    .shift(1)
                )

                track_data['Driver_Track_Races'] = range(len(track_data))

                track_features.append(track_data)

        result = pd.concat(track_features, ignore_index=True)
        logger.info(f"Created track history features for {len(result)} records")

        return result

    def create_championship_position_features(
        self,
        results_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create features based on championship standings

        Args:
            results_df: Race results

        Returns:
            DataFrame with championship position features
        """
        logger.info("Creating championship position features...")

        results_sorted = results_df.sort_values(['Year', 'RoundNumber'])

        champ_features = []

        for year in results_sorted['Year'].unique():
            year_data = results_sorted[results_sorted['Year'] == year].copy()

            for round_num in year_data['RoundNumber'].unique():
                round_data = year_data[year_data['RoundNumber'] == round_num].copy()

                prev_rounds = year_data[year_data['RoundNumber'] < round_num]

                if not prev_rounds.empty:
                    standings = (
                        prev_rounds.groupby('Abbreviation')['Points']
                        .sum()
                        .sort_values(ascending=False)
                        .reset_index()
                    )
                    standings['ChampionshipPosition'] = range(1, len(standings) + 1)

                    round_data = round_data.merge(
                        standings[['Abbreviation', 'ChampionshipPosition']],
                        on='Abbreviation',
                        how='left'
                    )
                    round_data['ChampionshipPosition'] = round_data['ChampionshipPosition'].fillna(20)
                else:
                    round_data['ChampionshipPosition'] = 20

                champ_features.append(round_data)

        result = pd.concat(champ_features, ignore_index=True)
        logger.info(f"Created championship features for {len(result)} records")

        return result

    def engineer_all_features(
        self,
        race_results: pd.DataFrame,
        qual_results: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create all features from race and qualifying data

        Args:
            race_results: Race results DataFrame
            qual_results: Qualifying results DataFrame

        Returns:
            Complete feature DataFrame
        """
        logger.info("Starting full feature engineering pipeline...")

        df = race_results.copy()

        df = self.create_driver_form_features(df)

        df = self.create_qualifying_features(df, qual_results)

        df = self.create_team_features(df)

        df = self.create_track_history_features(df)

        df = self.create_championship_position_features(df)

        df['RaceNumber'] = df['RoundNumber']
        df['IsHomeRace'] = 0

        logger.info(f"Feature engineering complete. Created {len(df)} samples with {len(df.columns)} features")

        return df


if __name__ == "__main__":
    from ml.data_pipeline import F1DataPipeline

    pipeline = F1DataPipeline(min_year=2023, max_year=2024)
    race_results, qual_results = pipeline.load_multi_season_data()

    if not race_results.empty:
        engineer = FeatureEngineer()
        features = engineer.engineer_all_features(race_results, qual_results)

        print(f"\nEngineered features shape: {features.shape}")
        print("\nFeature columns:")
        print(features.columns.tolist())
        print("\nSample data:")
        print(features.head())
