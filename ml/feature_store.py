"""
Feature Store Module (STORE State)
Manages storage and retrieval of engineered features
"""

import pandas as pd
import numpy as np
import os
import joblib
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import logging

from ml import MLConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureStore:
    """Manages feature storage and retrieval"""

    def __init__(self, base_path: str = None):
        """
        Initialize feature store

        Args:
            base_path: Base path for feature storage
        """
        self.base_path = base_path or MLConfig.FEATURE_STORE_PATH
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(os.path.join(self.base_path, "raw")).mkdir(exist_ok=True)
        Path(os.path.join(self.base_path, "processed")).mkdir(exist_ok=True)
        Path(os.path.join(self.base_path, "metadata")).mkdir(exist_ok=True)

    def save_features(
        self,
        features: pd.DataFrame,
        name: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Save feature DataFrame to store

        Args:
            features: Feature DataFrame
            name: Feature set name
            metadata: Optional metadata dictionary

        Returns:
            Path to saved features
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.parquet"
        filepath = os.path.join(self.base_path, "processed", filename)

        features.to_parquet(filepath, index=False)

        if metadata is None:
            metadata = {}

        metadata.update({
            'name': name,
            'timestamp': timestamp,
            'shape': features.shape,
            'columns': features.columns.tolist(),
            'dtypes': {col: str(dtype) for col, dtype in features.dtypes.items()}
        })

        metadata_path = os.path.join(
            self.base_path,
            "metadata",
            f"{name}_{timestamp}_metadata.pkl"
        )
        joblib.dump(metadata, metadata_path)

        logger.info(f"Saved features to {filepath}")
        logger.info(f"Features shape: {features.shape}")

        return filepath

    def load_features(self, name: str, version: str = "latest") -> pd.DataFrame:
        """
        Load features from store

        Args:
            name: Feature set name
            version: Version timestamp or "latest"

        Returns:
            Feature DataFrame
        """
        processed_path = os.path.join(self.base_path, "processed")

        if version == "latest":
            matching_files = sorted([
                f for f in os.listdir(processed_path)
                if f.startswith(name) and f.endswith('.parquet')
            ])

            if not matching_files:
                raise FileNotFoundError(f"No features found for {name}")

            filename = matching_files[-1]
        else:
            filename = f"{name}_{version}.parquet"

        filepath = os.path.join(processed_path, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Feature file not found: {filepath}")

        features = pd.read_parquet(filepath)
        logger.info(f"Loaded features from {filepath}")
        logger.info(f"Features shape: {features.shape}")

        return features

    def load_metadata(self, name: str, version: str = "latest") -> Dict:
        """
        Load feature metadata

        Args:
            name: Feature set name
            version: Version timestamp or "latest"

        Returns:
            Metadata dictionary
        """
        metadata_path = os.path.join(self.base_path, "metadata")

        if version == "latest":
            matching_files = sorted([
                f for f in os.listdir(metadata_path)
                if f.startswith(name) and f.endswith('_metadata.pkl')
            ])

            if not matching_files:
                raise FileNotFoundError(f"No metadata found for {name}")

            filename = matching_files[-1]
        else:
            filename = f"{name}_{version}_metadata.pkl"

        filepath = os.path.join(metadata_path, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Metadata file not found: {filepath}")

        metadata = joblib.load(filepath)
        logger.info(f"Loaded metadata from {filepath}")

        return metadata

    def list_available_features(self) -> List[Dict]:
        """
        List all available feature sets

        Returns:
            List of feature set information
        """
        processed_path = os.path.join(self.base_path, "processed")

        if not os.path.exists(processed_path):
            return []

        feature_files = [
            f for f in os.listdir(processed_path)
            if f.endswith('.parquet')
        ]

        feature_sets = []
        for filename in feature_files:
            parts = filename.replace('.parquet', '').split('_')
            if len(parts) >= 3:
                name = '_'.join(parts[:-2])
                timestamp = '_'.join(parts[-2:])

                filepath = os.path.join(processed_path, filename)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)

                feature_sets.append({
                    'name': name,
                    'timestamp': timestamp,
                    'filename': filename,
                    'size_mb': round(size_mb, 2)
                })

        feature_sets.sort(key=lambda x: x['timestamp'], reverse=True)

        return feature_sets

    def prepare_training_data(
        self,
        features: pd.DataFrame,
        target_col: str = 'Position',
        test_size: float = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare features for model training

        Args:
            features: Feature DataFrame
            target_col: Target column name
            test_size: Test split ratio

        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        if test_size is None:
            test_size = MLConfig.TEST_SPLIT_RATIO

        feature_cols = [
            col for col in features.columns
            if col not in [
                target_col, 'Year', 'EventName', 'RoundNumber',
                'Abbreviation', 'TeamName', 'FullName', 'Status',
                'Country', 'DriverNumber'
            ]
        ]

        features_clean = features.dropna(subset=feature_cols + [target_col])

        X = features_clean[feature_cols]
        y = features_clean[target_col]

        split_idx = int(len(X) * (1 - test_size))

        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]

        logger.info(f"Training set: {X_train.shape}, Test set: {X_test.shape}")
        logger.info(f"Feature columns: {len(feature_cols)}")

        return X_train, X_test, y_train, y_test

    def get_feature_importance_data(
        self,
        features: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Prepare data for feature importance analysis

        Args:
            features: Feature DataFrame

        Returns:
            DataFrame with feature statistics
        """
        exclude_cols = [
            'Position', 'Year', 'EventName', 'RoundNumber',
            'Abbreviation', 'TeamName', 'FullName', 'Status',
            'Country', 'DriverNumber'
        ]

        feature_cols = [col for col in features.columns if col not in exclude_cols]

        stats = []
        for col in feature_cols:
            stats.append({
                'feature': col,
                'mean': features[col].mean(),
                'std': features[col].std(),
                'min': features[col].min(),
                'max': features[col].max(),
                'missing_pct': features[col].isna().sum() / len(features) * 100
            })

        return pd.DataFrame(stats)


if __name__ == "__main__":
    store = FeatureStore()

    sample_data = pd.DataFrame({
        'Year': [2024] * 100,
        'Position': np.random.randint(1, 21, 100),
        'Points': np.random.randint(0, 26, 100),
        'AvgPosition_Last3': np.random.uniform(1, 20, 100),
        'Driver': ['VER'] * 100
    })

    filepath = store.save_features(sample_data, 'test_features')
    print(f"Saved to: {filepath}")

    loaded = store.load_features('test_features')
    print(f"\nLoaded shape: {loaded.shape}")

    available = store.list_available_features()
    print(f"\nAvailable feature sets: {len(available)}")
