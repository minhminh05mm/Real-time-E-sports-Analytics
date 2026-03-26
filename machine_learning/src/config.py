import os
from dataclasses import dataclass
from pathlib import Path

from clickhouse_driver import Client
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "machine_learning" / "data"
MODELS_DIR = ROOT_DIR / "machine_learning" / "models"
RAW_MATCHES_DIR = DATA_DIR / "raw_matches"
RAW_TIMELINES_DIR = DATA_DIR / "raw_timelines"
CHAMPION_SCALING_PATH = DATA_DIR / "champion_scaling.json"
TRAINING_DATA_PATH = DATA_DIR / "training_dataset_advanced.csv"
MODEL_PATH = MODELS_DIR / "win_rate_model.pkl"
LEGACY_MODEL_PATH = MODELS_DIR / "win_rate_model.legacy.json"
FEATURE_COLUMNS = ["minute", "gold_diff", "xp_diff", "obj_diff", "scaling_diff"]


@dataclass(frozen=True)
class Settings:
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_database: str
    riot_api_key: str
    riot_region: str
    riot_routing: str
    target_tier: str
    target_match_count: int
    matches_per_player: int


settings = Settings(
    clickhouse_host=os.getenv("CLICKHOUSE_HOST", "localhost"),
    clickhouse_port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
    clickhouse_user=os.getenv("CLICKHOUSE_USER", "admin"),
    clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", "admin123"),
    clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", "esports"),
    riot_api_key=os.getenv("RIOT_API_KEY", ""),
    riot_region=os.getenv("RIOT_REGION", "kr"),
    riot_routing=os.getenv("RIOT_ROUTING", "asia"),
    target_tier=os.getenv("ML_TARGET_TIER", "MASTER"),
    target_match_count=int(os.getenv("ML_TARGET_MATCH_COUNT", "1000")),
    matches_per_player=int(os.getenv("ML_MATCHES_PER_PLAYER", "25")),
)


def get_clickhouse_client(database: str | None = None) -> Client:
    return Client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=database or settings.clickhouse_database,
    )
