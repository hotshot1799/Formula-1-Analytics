# F1 ML Prediction System

A state machine-based machine learning pipeline for Formula 1 race predictions.

## Architecture

The system implements a state machine workflow with the following states:

```
IDLE → INGEST → ENGINEER → STORE → [MODELS] → EVALUATE → COMPLETE
```

### States

1. **IDLE**: Initial state, ready to begin
2. **INGEST**: Load F1 race and qualifying data from FastF1
3. **ENGINEER**: Create features from raw data
4. **STORE**: Save features to feature store and prepare train/test splits
5. **ELO**: Train ELO rating model (more models coming soon)
6. **EVALUATE**: Evaluate all trained models
7. **COMPLETE**: Pipeline finished successfully

## Components

### Data Pipeline (`data_pipeline.py`)
- Loads race results and qualifying data from FastF1 API
- Retrieves driver and constructor standings
- Supports multi-season data collection
- Handles data validation and error recovery

### Feature Engineering (`feature_engine.py`)
- **Driver Form Features**: Rolling averages of recent performance (last 3, 5 races)
- **Qualifying Features**: Grid position and qualifying performance
- **Team Features**: Team-level performance metrics
- **Track History**: Driver performance at specific circuits
- **Championship Features**: Current championship standings

### Feature Store (`feature_store.py`)
- Persistent storage for engineered features
- Version control for feature sets
- Metadata tracking
- Train/test split preparation
- Feature importance analysis

### Models

#### Base Model (`models/base.py`)
- Abstract base class for all F1 models
- Standard prediction and evaluation interface
- Ensemble model support

#### ELO Model (`models/elo.py`)
- Classic ELO rating system adapted for F1
- Tracks driver ratings over time
- Head-to-head predictions
- Current driver rankings

**Coming Soon:**
- XGBoost: Gradient boosting for position prediction
- Ranker: Learning-to-rank model
- Tyre Degradation: Physics-based tyre wear model
- Bayesian: Probabilistic predictions
- Monte Carlo: Simulation-based predictions
- Ensemble: Combining multiple models

### Evaluation (`evaluation.py`)
- Comprehensive metrics:
  - MAE, RMSE, R²
  - Top-3, Top-5, Top-10 accuracy
  - Podium prediction accuracy
  - Points finish accuracy
  - Position-wise accuracy
- Model comparison
- Cross-validation support
- Confidence metrics

### Pipeline Controller (`pipeline.py`)
- Orchestrates entire workflow
- State management
- End-to-end execution
- Status tracking

## Quick Start

### Run Complete Pipeline

```python
from ml.pipeline import F1MLPipeline

# Initialize pipeline for 2023-2024 seasons
pipeline = F1MLPipeline(min_year=2023, max_year=2024)

# Run complete pipeline
success = pipeline.run_complete_pipeline()

# Check status
status = pipeline.get_pipeline_status()
print(status)
```

### Use Individual Components

```python
# Load data
from ml.data_pipeline import F1DataPipeline
pipeline = F1DataPipeline(min_year=2023, max_year=2024)
race_results, qual_results = pipeline.load_multi_season_data()

# Engineer features
from ml.feature_engine import FeatureEngineer
engineer = FeatureEngineer()
features = engineer.engineer_all_features(race_results, qual_results)

# Train ELO model
from ml.models.elo import ELOModel
elo = ELOModel()
elo.train(X_train, y_train)
predictions = elo.predict(X_test)

# Evaluate
from ml.evaluation import ModelEvaluator
evaluator = ModelEvaluator()
metrics = evaluator.evaluate_position_predictions(y_true, y_pred)
```

## Configuration

Edit `ml/__init__.py` to configure:

```python
class MLConfig:
    # Data settings
    MIN_YEAR = 2018
    MAX_YEAR = 2025

    # Feature engineering
    FEATURE_WINDOW_RACES = 5

    # Model settings
    ELO_K_FACTOR = 32
    ELO_INITIAL_RATING = 1500

    # Evaluation
    TEST_SPLIT_RATIO = 0.2
    CROSS_VALIDATION_FOLDS = 5
```

## Directory Structure

```
ml/
├── __init__.py           # Config and state definitions
├── data_pipeline.py      # Data ingestion (INGEST)
├── feature_engine.py     # Feature engineering (ENGINEER)
├── feature_store.py      # Feature storage (STORE)
├── evaluation.py         # Model evaluation (EVALUATE)
├── pipeline.py           # State machine controller
├── models/
│   ├── __init__.py
│   ├── base.py          # Base model classes
│   └── elo.py           # ELO rating model
├── utils/
│   └── __init__.py
└── data/                # Created at runtime
    ├── features/        # Stored feature sets
    ├── models/          # Saved model files
    └── cache/           # FastF1 cache
```

## Future Enhancements

### Phase 2: Advanced Models
- [ ] XGBoost model
- [ ] Learning-to-rank model
- [ ] Neural network models

### Phase 3: Domain-Specific Models
- [ ] Tyre degradation model
- [ ] Weather impact model
- [ ] Safety car probability

### Phase 4: Ensemble & Production
- [ ] Ensemble meta-model
- [ ] Model versioning
- [ ] API endpoints
- [ ] Real-time predictions
- [ ] Integration with Streamlit UI

## Dependencies

```
fastf1
pandas
numpy
scikit-learn
xgboost
scipy
joblib
```

## License

Part of the Formula 1 Analytics project.
