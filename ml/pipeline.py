"""
ML Pipeline State Machine Controller
Orchestrates the entire F1 ML prediction workflow
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

from ml import MLState, MLConfig
from ml.data_pipeline import F1DataPipeline
from ml.feature_engine import FeatureEngineer
from ml.feature_store import FeatureStore
from ml.models.elo import ELOModel
from ml.evaluation import ModelEvaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class F1MLPipeline:
    """
    State machine-based ML pipeline for F1 predictions
    Follows the workflow: IDLE -> INGEST -> ENGINEER -> STORE -> MODEL -> EVALUATE -> COMPLETE
    """

    def __init__(self, min_year: int = None, max_year: int = None):
        """
        Initialize ML pipeline

        Args:
            min_year: Minimum year for data collection
            max_year: Maximum year for data collection
        """
        self.state = MLState.IDLE
        self.min_year = min_year or MLConfig.MIN_YEAR
        self.max_year = max_year or MLConfig.MAX_YEAR

        self.data_pipeline = F1DataPipeline(self.min_year, self.max_year)
        self.feature_engineer = FeatureEngineer()
        self.feature_store = FeatureStore()
        self.evaluator = ModelEvaluator()

        self.race_results: Optional[pd.DataFrame] = None
        self.qual_results: Optional[pd.DataFrame] = None
        self.features: Optional[pd.DataFrame] = None
        self.models: Dict[str, any] = {}

        self.X_train: Optional[pd.DataFrame] = None
        self.X_test: Optional[pd.DataFrame] = None
        self.y_train: Optional[pd.Series] = None
        self.y_test: Optional[pd.Series] = None

    def transition_to(self, new_state: MLState) -> None:
        """
        Transition to a new state

        Args:
            new_state: Target state
        """
        logger.info(f"State transition: {self.state.value} -> {new_state.value}")
        self.state = new_state

    def run_ingest_state(self, years: Optional[List[int]] = None) -> bool:
        """
        INGEST state: Load F1 data

        Args:
            years: Optional list of years to load

        Returns:
            Success status
        """
        logger.info("=" * 60)
        logger.info("STARTING INGEST STATE")
        logger.info("=" * 60)

        self.transition_to(MLState.INGEST)

        try:
            self.race_results, self.qual_results = self.data_pipeline.load_multi_season_data(years)

            if self.race_results.empty:
                logger.error("Failed to load race data")
                return False

            logger.info(f"Loaded {len(self.race_results)} race results")
            logger.info(f"Loaded {len(self.qual_results)} qualifying results")

            return True

        except Exception as e:
            logger.error(f"Error in INGEST state: {e}")
            return False

    def run_engineer_state(self) -> bool:
        """
        ENGINEER state: Create features

        Returns:
            Success status
        """
        logger.info("=" * 60)
        logger.info("STARTING ENGINEER STATE")
        logger.info("=" * 60)

        self.transition_to(MLState.ENGINEER)

        try:
            if self.race_results is None or self.race_results.empty:
                logger.error("No race data available for feature engineering")
                return False

            self.features = self.feature_engineer.engineer_all_features(
                self.race_results,
                self.qual_results
            )

            logger.info(f"Created {self.features.shape[1]} features")

            return True

        except Exception as e:
            logger.error(f"Error in ENGINEER state: {e}")
            return False

    def run_store_state(self, feature_name: str = "f1_features") -> bool:
        """
        STORE state: Save features to feature store

        Args:
            feature_name: Name for feature set

        Returns:
            Success status
        """
        logger.info("=" * 60)
        logger.info("STARTING STORE STATE")
        logger.info("=" * 60)

        self.transition_to(MLState.STORE)

        try:
            if self.features is None or self.features.empty:
                logger.error("No features available to store")
                return False

            filepath = self.feature_store.save_features(
                self.features,
                feature_name,
                metadata={
                    'min_year': self.min_year,
                    'max_year': self.max_year,
                    'n_races': len(self.features['EventName'].unique())
                }
            )

            logger.info(f"Features saved to {filepath}")

            # Pass ELO metadata so the model can group races and find drivers.
            # Without these columns X_train has no 'Abbreviation', causing
            # the ELO train loop to see an empty driver list and leave every
            # rating at the initial 1500.
            self.X_train, self.X_test, self.y_train, self.y_test = (
                self.feature_store.prepare_training_data(
                    self.features,
                    metadata_cols=['Abbreviation', 'Year', 'EventName', 'RoundNumber'],
                )
            )

            logger.info(f"Training set: {len(self.X_train)} samples")
            logger.info(f"Test set: {len(self.X_test)} samples")

            return True

        except Exception as e:
            logger.error(f"Error in STORE state: {e}")
            return False

    def run_elo_model_state(self) -> bool:
        """
        ELO state: Train ELO rating model

        Returns:
            Success status
        """
        logger.info("=" * 60)
        logger.info("STARTING ELO MODEL STATE")
        logger.info("=" * 60)

        self.transition_to(MLState.ELO)

        try:
            if self.X_train is None:
                logger.error("No training data available")
                return False

            elo_model = ELOModel()
            elo_model.train(self.X_train, self.y_train)

            self.models['ELO'] = elo_model

            rankings = elo_model.get_current_rankings()
            logger.info("\nTop 10 ELO Rankings:")
            logger.info(rankings.head(10).to_string(index=False))

            return True

        except Exception as e:
            logger.error(f"Error in ELO state: {e}")
            return False

    def run_evaluate_state(self) -> bool:
        """
        EVALUATE state: Evaluate all trained models

        Returns:
            Success status
        """
        logger.info("=" * 60)
        logger.info("STARTING EVALUATE STATE")
        logger.info("=" * 60)

        self.transition_to(MLState.EVALUATE)

        try:
            if not self.models:
                logger.error("No models available for evaluation")
                return False

            if self.X_test is None or self.y_test is None:
                logger.error("No test data available")
                return False

            predictions = {}

            for model_name, model in self.models.items():
                logger.info(f"\nEvaluating {model_name}...")
                y_pred = model.predict(self.X_test)
                predictions[model_name] = y_pred

            comparison = self.evaluator.evaluate_multiple_models(
                self.y_test.values,
                predictions
            )

            logger.info("\nModel Comparison:")
            logger.info(comparison.to_string(index=False))

            best_model, best_score = self.evaluator.get_best_model('mae')
            logger.info(f"\nBest Model: {best_model} (MAE: {best_score:.2f})")

            return True

        except Exception as e:
            logger.error(f"Error in EVALUATE state: {e}")
            return False

    def run_complete_pipeline(
        self,
        years: Optional[List[int]] = None,
        feature_name: str = "f1_features"
    ) -> bool:
        """
        Run the complete ML pipeline from start to finish

        Args:
            years: Optional list of years to process
            feature_name: Name for feature set

        Returns:
            Success status
        """
        logger.info("\n" + "=" * 60)
        logger.info("STARTING F1 ML PIPELINE")
        logger.info("=" * 60 + "\n")

        if not self.run_ingest_state(years):
            logger.error("Pipeline failed at INGEST state")
            return False

        if not self.run_engineer_state():
            logger.error("Pipeline failed at ENGINEER state")
            return False

        if not self.run_store_state(feature_name):
            logger.error("Pipeline failed at STORE state")
            return False

        if not self.run_elo_model_state():
            logger.error("Pipeline failed at ELO state")
            return False

        if not self.run_evaluate_state():
            logger.error("Pipeline failed at EVALUATE state")
            return False

        self.transition_to(MLState.COMPLETE)

        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

        return True

    def get_model(self, model_name: str):
        """
        Get a trained model by name

        Args:
            model_name: Name of the model

        Returns:
            Trained model
        """
        return self.models.get(model_name)

    def get_predictions(self, model_name: str, X: pd.DataFrame) -> np.ndarray:
        """
        Get predictions from a specific model

        Args:
            model_name: Name of the model
            X: Feature DataFrame

        Returns:
            Predictions
        """
        model = self.get_model(model_name)
        if model is None:
            raise ValueError(f"Model {model_name} not found")

        return model.predict(X)

    def get_pipeline_status(self) -> Dict:
        """
        Get current pipeline status

        Returns:
            Status dictionary
        """
        return {
            'state': self.state.value,
            'data_loaded': self.race_results is not None,
            'features_created': self.features is not None,
            'models_trained': list(self.models.keys()),
            'n_races': len(self.race_results) if self.race_results is not None else 0,
            'n_features': self.features.shape[1] if self.features is not None else 0
        }


if __name__ == "__main__":
    pipeline = F1MLPipeline(min_year=2023, max_year=2024)

    success = pipeline.run_complete_pipeline()

    if success:
        status = pipeline.get_pipeline_status()
        print("\nPipeline Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
