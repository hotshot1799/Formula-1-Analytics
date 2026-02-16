"""
Model Evaluation Module
Provides comprehensive evaluation metrics for F1 prediction models
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Evaluates F1 prediction model performance"""

    def __init__(self):
        """Initialize evaluator"""
        self.results = {}

    def evaluate_position_predictions(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str = "Model"
    ) -> Dict[str, float]:
        """
        Evaluate race position predictions

        Args:
            y_true: True positions
            y_pred: Predicted positions
            model_name: Name of the model

        Returns:
            Dictionary of metrics
        """
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)

        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)

        top3_accuracy = np.mean((y_pred <= 3) == (y_true <= 3))
        top5_accuracy = np.mean((y_pred <= 5) == (y_true <= 5))
        top10_accuracy = np.mean((y_pred <= 10) == (y_true <= 10))

        podium_true = (y_true <= 3).astype(int)
        podium_pred = (y_pred <= 3).astype(int)
        podium_accuracy = accuracy_score(podium_true, podium_pred)

        points_true = (y_true <= 10).astype(int)
        points_pred = (y_pred <= 10).astype(int)
        points_accuracy = accuracy_score(points_true, points_pred)

        exact_accuracy = np.mean(y_true == np.round(y_pred))

        within_1 = np.mean(np.abs(y_true - y_pred) <= 1)
        within_2 = np.mean(np.abs(y_true - y_pred) <= 2)
        within_3 = np.mean(np.abs(y_true - y_pred) <= 3)

        metrics = {
            'mae': float(mae),
            'rmse': float(rmse),
            'r2': float(r2),
            'top3_accuracy': float(top3_accuracy),
            'top5_accuracy': float(top5_accuracy),
            'top10_accuracy': float(top10_accuracy),
            'podium_accuracy': float(podium_accuracy),
            'points_accuracy': float(points_accuracy),
            'exact_accuracy': float(exact_accuracy),
            'within_1_position': float(within_1),
            'within_2_positions': float(within_2),
            'within_3_positions': float(within_3)
        }

        self.results[model_name] = metrics

        logger.info(f"\n{model_name} Evaluation:")
        logger.info(f"  MAE: {mae:.2f}")
        logger.info(f"  RMSE: {rmse:.2f}")
        logger.info(f"  R²: {r2:.3f}")
        logger.info(f"  Top-3 Accuracy: {top3_accuracy:.1%}")
        logger.info(f"  Podium Accuracy: {podium_accuracy:.1%}")
        logger.info(f"  Points Accuracy: {points_accuracy:.1%}")

        return metrics

    def evaluate_multiple_models(
        self,
        y_true: np.ndarray,
        predictions: Dict[str, np.ndarray]
    ) -> pd.DataFrame:
        """
        Evaluate multiple models and compare

        Args:
            y_true: True values
            predictions: Dictionary mapping model names to predictions

        Returns:
            DataFrame with comparison results
        """
        results = []

        for model_name, y_pred in predictions.items():
            metrics = self.evaluate_position_predictions(y_true, y_pred, model_name)
            metrics['model'] = model_name
            results.append(metrics)

        df = pd.DataFrame(results)
        df = df[['model'] + [col for col in df.columns if col != 'model']]

        return df

    def compare_models(self) -> pd.DataFrame:
        """
        Compare all evaluated models

        Returns:
            DataFrame with model comparison
        """
        if not self.results:
            logger.warning("No models have been evaluated yet")
            return pd.DataFrame()

        comparison = pd.DataFrame(self.results).T
        comparison = comparison.sort_values('mae')

        return comparison

    def get_best_model(self, metric: str = 'mae') -> Tuple[str, float]:
        """
        Get the best performing model

        Args:
            metric: Metric to use for comparison (lower is better for MAE/RMSE)

        Returns:
            Tuple of (model_name, metric_value)
        """
        if not self.results:
            raise ValueError("No models have been evaluated yet")

        if metric in ['mae', 'rmse']:
            best_model = min(self.results.items(), key=lambda x: x[1][metric])
        else:
            best_model = max(self.results.items(), key=lambda x: x[1][metric])

        return best_model[0], best_model[1][metric]

    def calculate_prediction_confidence(
        self,
        predictions: np.ndarray,
        true_positions: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate confidence metrics for predictions

        Args:
            predictions: Model predictions
            true_positions: True positions

        Returns:
            Confidence metrics
        """
        errors = np.abs(predictions - true_positions)

        confidence = {
            'mean_error': float(np.mean(errors)),
            'median_error': float(np.median(errors)),
            'std_error': float(np.std(errors)),
            'max_error': float(np.max(errors)),
            'prediction_variance': float(np.var(predictions))
        }

        return confidence

    def evaluate_by_position_group(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> pd.DataFrame:
        """
        Evaluate predictions by position groups (front, mid, back)

        Args:
            y_true: True positions
            y_pred: Predicted positions

        Returns:
            DataFrame with group-wise metrics
        """
        groups = {
            'Front (1-5)': (y_true <= 5),
            'Midfield (6-10)': (y_true > 5) & (y_true <= 10),
            'Back (11-20)': (y_true > 10)
        }

        results = []

        for group_name, mask in groups.items():
            if mask.sum() > 0:
                group_mae = mean_absolute_error(y_true[mask], y_pred[mask])
                group_rmse = np.sqrt(mean_squared_error(y_true[mask], y_pred[mask]))

                results.append({
                    'group': group_name,
                    'count': int(mask.sum()),
                    'mae': float(group_mae),
                    'rmse': float(group_rmse)
                })

        return pd.DataFrame(results)

    def cross_validate_performance(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        n_folds: int = 5
    ) -> Dict[str, List[float]]:
        """
        Perform cross-validation style evaluation

        Args:
            y_true: True values
            y_pred: Predictions
            n_folds: Number of folds

        Returns:
            Dictionary with metrics per fold
        """
        fold_size = len(y_true) // n_folds
        fold_metrics = {
            'mae': [],
            'rmse': [],
            'top3_accuracy': []
        }

        for i in range(n_folds):
            start_idx = i * fold_size
            end_idx = start_idx + fold_size if i < n_folds - 1 else len(y_true)

            fold_true = y_true[start_idx:end_idx]
            fold_pred = y_pred[start_idx:end_idx]

            fold_metrics['mae'].append(mean_absolute_error(fold_true, fold_pred))
            fold_metrics['rmse'].append(np.sqrt(mean_squared_error(fold_true, fold_pred)))
            fold_metrics['top3_accuracy'].append(
                np.mean((fold_pred <= 3) == (fold_true <= 3))
            )

        fold_metrics['mae_mean'] = np.mean(fold_metrics['mae'])
        fold_metrics['mae_std'] = np.std(fold_metrics['mae'])

        return fold_metrics


if __name__ == "__main__":
    np.random.seed(42)
    y_true = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    y_pred_model1 = y_true + np.random.normal(0, 1, len(y_true))
    y_pred_model2 = y_true + np.random.normal(0, 2, len(y_true))

    evaluator = ModelEvaluator()

    metrics1 = evaluator.evaluate_position_predictions(y_true, y_pred_model1, "Model 1")
    metrics2 = evaluator.evaluate_position_predictions(y_true, y_pred_model2, "Model 2")

    comparison = evaluator.compare_models()
    print("\nModel Comparison:")
    print(comparison[['mae', 'rmse', 'podium_accuracy']])

    best_model, best_score = evaluator.get_best_model('mae')
    print(f"\nBest model: {best_model} (MAE: {best_score:.2f})")
