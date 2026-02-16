"""
Data Pipeline Module (INGEST State)
Loads and preprocesses F1 data for ML training
"""

import fastf1
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

from ml import MLConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class F1DataPipeline:
    """Handles data ingestion from FastF1 API"""

    def __init__(self, min_year: int = None, max_year: int = None):
        """
        Initialize data pipeline

        Args:
            min_year: Minimum year for data collection
            max_year: Maximum year for data collection
        """
        self.min_year = min_year or MLConfig.MIN_YEAR
        self.max_year = max_year or MLConfig.MAX_YEAR
        self.cache_enabled = True

    def load_season_results(self, year: int) -> pd.DataFrame:
        """
        Load all race results for a season

        Args:
            year: Season year

        Returns:
            DataFrame with race results
        """
        try:
            logger.info(f"Loading {year} season results...")
            schedule = fastf1.get_event_schedule(year)

            all_results = []

            for _, event in schedule.iterrows():
                if event['EventFormat'] != 'conventional':
                    continue

                try:
                    session = fastf1.get_session(year, event['EventName'], 'R')
                    session.load()

                    results = session.results
                    results['Year'] = year
                    results['EventName'] = event['EventName']
                    results['RoundNumber'] = event['RoundNumber']
                    results['Country'] = event['Country']

                    all_results.append(results)

                except Exception as e:
                    logger.warning(f"Failed to load {event['EventName']}: {e}")
                    continue

            if all_results:
                df = pd.concat(all_results, ignore_index=True)
                logger.info(f"Loaded {len(df)} results from {year}")
                return df
            else:
                logger.warning(f"No results loaded for {year}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading season {year}: {e}")
            return pd.DataFrame()

    def load_qualifying_results(self, year: int) -> pd.DataFrame:
        """
        Load qualifying results for a season

        Args:
            year: Season year

        Returns:
            DataFrame with qualifying results
        """
        try:
            logger.info(f"Loading {year} qualifying results...")
            schedule = fastf1.get_event_schedule(year)

            all_results = []

            for _, event in schedule.iterrows():
                if event['EventFormat'] != 'conventional':
                    continue

                try:
                    session = fastf1.get_session(year, event['EventName'], 'Q')
                    session.load()

                    results = session.results
                    results['Year'] = year
                    results['EventName'] = event['EventName']
                    results['RoundNumber'] = event['RoundNumber']

                    all_results.append(results)

                except Exception as e:
                    logger.warning(f"Failed to load qualifying for {event['EventName']}: {e}")
                    continue

            if all_results:
                df = pd.concat(all_results, ignore_index=True)
                logger.info(f"Loaded {len(df)} qualifying results from {year}")
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading qualifying {year}: {e}")
            return pd.DataFrame()

    def load_multi_season_data(
        self,
        years: Optional[List[int]] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load data for multiple seasons

        Args:
            years: List of years to load. If None, loads all years from min_year to max_year

        Returns:
            Tuple of (race_results, qualifying_results)
        """
        if years is None:
            years = list(range(self.min_year, self.max_year + 1))

        all_race_results = []
        all_qual_results = []

        for year in years:
            race_df = self.load_season_results(year)
            if not race_df.empty:
                all_race_results.append(race_df)

            qual_df = self.load_qualifying_results(year)
            if not qual_df.empty:
                all_qual_results.append(qual_df)

        race_results = pd.concat(all_race_results, ignore_index=True) if all_race_results else pd.DataFrame()
        qual_results = pd.concat(all_qual_results, ignore_index=True) if all_qual_results else pd.DataFrame()

        logger.info(f"Total loaded: {len(race_results)} race results, {len(qual_results)} qualifying results")

        return race_results, qual_results

    def get_driver_standings(self, year: int, round_num: int) -> pd.DataFrame:
        """
        Get driver standings up to a specific round

        Args:
            year: Season year
            round_num: Round number

        Returns:
            DataFrame with driver standings
        """
        try:
            schedule = fastf1.get_event_schedule(year)
            standings_data = []

            for _, event in schedule.iterrows():
                if event['RoundNumber'] > round_num:
                    break

                if event['EventFormat'] != 'conventional':
                    continue

                try:
                    session = fastf1.get_session(year, event['EventName'], 'R')
                    session.load()

                    results = session.results
                    for _, driver in results.iterrows():
                        standings_data.append({
                            'Driver': driver['Abbreviation'],
                            'Points': driver.get('Points', 0),
                            'RoundNumber': event['RoundNumber']
                        })

                except Exception as e:
                    logger.warning(f"Failed to load standings for {event['EventName']}: {e}")
                    continue

            if standings_data:
                df = pd.DataFrame(standings_data)
                standings = df.groupby('Driver')['Points'].sum().reset_index()
                standings = standings.sort_values('Points', ascending=False)
                return standings
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading standings for {year} round {round_num}: {e}")
            return pd.DataFrame()

    def get_constructor_standings(self, year: int, round_num: int) -> pd.DataFrame:
        """
        Get constructor standings up to a specific round

        Args:
            year: Season year
            round_num: Round number

        Returns:
            DataFrame with constructor standings
        """
        try:
            schedule = fastf1.get_event_schedule(year)
            standings_data = []

            for _, event in schedule.iterrows():
                if event['RoundNumber'] > round_num:
                    break

                if event['EventFormat'] != 'conventional':
                    continue

                try:
                    session = fastf1.get_session(year, event['EventName'], 'R')
                    session.load()

                    results = session.results
                    for _, driver in results.iterrows():
                        standings_data.append({
                            'Team': driver['TeamName'],
                            'Points': driver.get('Points', 0),
                            'RoundNumber': event['RoundNumber']
                        })

                except Exception as e:
                    logger.warning(f"Failed to load constructor standings for {event['EventName']}: {e}")
                    continue

            if standings_data:
                df = pd.DataFrame(standings_data)
                standings = df.groupby('Team')['Points'].sum().reset_index()
                standings = standings.sort_values('Points', ascending=False)
                return standings
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading constructor standings for {year} round {round_num}: {e}")
            return pd.DataFrame()


if __name__ == "__main__":
    pipeline = F1DataPipeline(min_year=2023, max_year=2024)
    race_results, qual_results = pipeline.load_multi_season_data()

    print(f"\nLoaded {len(race_results)} race results")
    print(f"Loaded {len(qual_results)} qualifying results")

    if not race_results.empty:
        print("\nSample race results:")
        print(race_results[['Year', 'EventName', 'Abbreviation', 'Position', 'Points']].head())
