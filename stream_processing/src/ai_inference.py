import json
from pathlib import Path

import joblib
import pandas as pd
import xgboost as xgb

from stream_processing.src.config import FEATURE_COLUMNS, settings


def load_scaling_map(path: Path | None = None) -> dict:
    scaling_path = path or settings.champion_scaling_path
    if not scaling_path.exists():
        return {}

    with scaling_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def get_scaling_score(champion_name: str | None, scaling_map: dict) -> int:
    if not champion_name:
        return 5

    clean_name = champion_name.replace(" ", "").replace("'", "").replace(".", "").lower()
    for key, value in scaling_map.items():
        if key == "_COMMENT":
            continue
        clean_key = key.replace(" ", "").replace("'", "").replace(".", "").lower()
        if clean_name == clean_key:
            return value
    return 5


def calculate_scaling_diff(participant_lookup: dict[int, dict], scaling_map: dict) -> int:
    blue_score = 0
    red_score = 0

    for player in participant_lookup.values():
        champion_name = player.get("champion_name")
        score = get_scaling_score(champion_name, scaling_map)
        if player.get("team_id") == 100:
            blue_score += score
        elif player.get("team_id") == 200:
            red_score += score

    return blue_score - red_score


def load_model():
    if settings.model_path.exists():
        return joblib.load(settings.model_path)

    if settings.legacy_model_path.exists():
        model = xgb.XGBClassifier()
        model.load_model(settings.legacy_model_path)
        return model

    print(
        "Model artifact not found. Run `python -m machine_learning.src.train_xgboost` first."
    )
    return None


def predict_blue_win_rate(model, feature_row: dict) -> float:
    if model is None:
        return 50.0

    frame = pd.DataFrame([{column: feature_row[column] for column in FEATURE_COLUMNS}])
    if hasattr(model, "predict_proba"):
        return float(model.predict_proba(frame)[0][1] * 100.0)

    dmatrix = xgb.DMatrix(frame)
    return float(model.predict(dmatrix)[0] * 100.0)
