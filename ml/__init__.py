"""
F1 ML Prediction System
Implements a state machine-based ML pipeline for F1 race predictions
"""

__version__ = "0.1.0"

from enum import Enum


class MLState(Enum):
    """State machine states for ML pipeline"""
    IDLE = "idle"
    INGEST = "ingest"
    ENGINEER = "engineer"
    STORE = "store"
    ELO = "elo"
    XGBOOST = "xgboost"
    RANKER = "ranker"
    TYRE_DEG = "tyre_degradation"
    BAYESIAN = "bayesian"
    MONTE_CARLO = "monte_carlo"
    ENSEMBLE = "ensemble"
    EVALUATE = "evaluate"
    COMPLETE = "complete"


class MLConfig:
    """Central configuration for ML pipeline"""

    # Data settings
    MIN_YEAR = 2018
    MAX_YEAR = 2025

    # Feature engineering
    FEATURE_WINDOW_RACES = 5  # Look back at last N races for rolling features

    # Model settings
    ELO_K_FACTOR = 32
    ELO_INITIAL_RATING = 1500

    # Evaluation
    TEST_SPLIT_RATIO = 0.2
    CROSS_VALIDATION_FOLDS = 5

    # Storage
    FEATURE_STORE_PATH = "ml/data/features"
    MODEL_STORE_PATH = "ml/data/models"
    CACHE_PATH = "ml/data/cache"


__all__ = ['MLState', 'MLConfig']
