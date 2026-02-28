"""
Base Model Classes for F1 Predictions
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseF1Model(ABC):
    """Abstract base class for all F1 prediction models"""

    # Subclasses override this to declare the extra columns they need
    # beyond the default numeric features (e.g. identifier columns).
    required_columns: List[str] = []

    def __init__(self, name: str):
        """
        Initialize base model

        Args:
            name: Model name
        """
        self.name = name
        self.is_trained = False
        self.metadata = {}

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """
        Train the model

        Args:
            X: Training features
            y: Training targets
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions

        Args:
            X: Feature DataFrame

        Returns:
            Predictions array
        """
        pass

    def prepare_input(self, X: pd.DataFrame, meta: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Combine X and meta into the input this model needs.

        The default implementation returns X as-is.  Models that need
        identifier columns (listed in ``required_columns``) will merge
        them from *meta* when they are not already present in *X*.
        """
        if not self.required_columns:
            return X

        missing = [c for c in self.required_columns if c not in X.columns]
        if not missing:
            return X

        if meta is None or meta.empty:
            raise ValueError(
                f"{self.name} requires columns {missing} but meta is empty"
            )

        available = [c for c in missing if c in meta.columns]
        if available:
            return pd.concat(
                [X.reset_index(drop=True), meta[available].reset_index(drop=True)],
                axis=1,
            )
        raise ValueError(
            f"{self.name} requires columns {missing} but they are not in X or meta"
        )

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        Evaluate model performance

        Args:
            X: Test features
            y: Test targets

        Returns:
            Dictionary of metrics
        """
        predictions = self.predict(X)

        mae = np.mean(np.abs(predictions - y))
        rmse = np.sqrt(np.mean((predictions - y) ** 2))

        top3_accuracy = np.mean((predictions <= 3) == (y <= 3))
        top10_accuracy = np.mean((predictions <= 10) == (y <= 10))

        metrics = {
            'mae': mae,
            'rmse': rmse,
            'top3_accuracy': top3_accuracy,
            'top10_accuracy': top10_accuracy
        }

        logger.info(f"{self.name} - MAE: {mae:.2f}, RMSE: {rmse:.2f}")

        return metrics

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get model metadata

        Returns:
            Metadata dictionary
        """
        return {
            'name': self.name,
            'is_trained': self.is_trained,
            **self.metadata
        }

    def save(self, filepath: str) -> None:
        """
        Save model to disk

        Args:
            filepath: Path to save model
        """
        import joblib
        joblib.dump(self, filepath)
        logger.info(f"Saved {self.name} to {filepath}")

    @staticmethod
    def load(filepath: str) -> 'BaseF1Model':
        """
        Load model from disk

        Args:
            filepath: Path to model file

        Returns:
            Loaded model
        """
        import joblib
        model = joblib.load(filepath)
        logger.info(f"Loaded {model.name} from {filepath}")
        return model


class EnsembleModel(BaseF1Model):
    """Ensemble model that combines multiple models"""

    def __init__(self, models: List[BaseF1Model], weights: Optional[List[float]] = None):
        """
        Initialize ensemble model

        Args:
            models: List of models to ensemble
            weights: Optional weights for each model (defaults to equal weights)
        """
        super().__init__("Ensemble")
        self.models = models
        self.weights = weights or [1.0 / len(models)] * len(models)

        if len(self.weights) != len(self.models):
            raise ValueError("Number of weights must match number of models")

        if not np.isclose(sum(self.weights), 1.0):
            raise ValueError("Weights must sum to 1.0")

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """
        Train all models in ensemble

        Args:
            X: Training features
            y: Training targets
        """
        logger.info(f"Training ensemble with {len(self.models)} models")

        for model in self.models:
            logger.info(f"Training {model.name}...")
            model.train(X, y)

        self.is_trained = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make weighted ensemble predictions

        Args:
            X: Feature DataFrame

        Returns:
            Weighted predictions
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        predictions = []

        for model, weight in zip(self.models, self.weights):
            pred = model.predict(X)
            predictions.append(pred * weight)

        ensemble_pred = np.sum(predictions, axis=0)

        return ensemble_pred

    def get_model_predictions(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Get individual predictions from each model

        Args:
            X: Feature DataFrame

        Returns:
            Dictionary mapping model names to predictions
        """
        return {model.name: model.predict(X) for model in self.models}


if __name__ == "__main__":
    print("Base model classes defined")
    print("Available base classes: BaseF1Model, EnsembleModel")
