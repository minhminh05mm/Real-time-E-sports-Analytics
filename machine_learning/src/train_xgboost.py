import joblib
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from machine_learning.src.config import (
    FEATURE_COLUMNS,
    LEGACY_MODEL_PATH,
    MODEL_PATH,
    TRAINING_DATA_PATH,
)


def train_model() -> None:
    print("Starting XGBoost training job")

    if not TRAINING_DATA_PATH.exists():
        print(f"Training dataset not found: {TRAINING_DATA_PATH}")
        return

    df = pd.read_csv(TRAINING_DATA_PATH)
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Validation accuracy: {accuracy * 100:.2f}%")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    model.save_model(LEGACY_MODEL_PATH)
    print(f"Saved pickle model to {MODEL_PATH}")
    print(f"Saved legacy XGBoost JSON to {LEGACY_MODEL_PATH}")

    importances = pd.DataFrame(
        {"feature": FEATURE_COLUMNS, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)
    print(importances.to_string(index=False))


if __name__ == "__main__":
    train_model()
