import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

FEATURE_COLUMNS = ["minute", "gold_diff", "xp_diff", "obj_diff", "scaling_diff"]
TRACKED_EVENT_TYPES = {
    "CHAMPION_KILL",
    "WARD_PLACED",
    "TURRET_PLATE_DESTROYED",
    "ELITE_MONSTER_KILL",
    "BUILDING_KILL",
}
OBJECTIVE_EVENT_TYPES = {
    "TURRET_PLATE_DESTROYED",
    "ELITE_MONSTER_KILL",
    "BUILDING_KILL",
}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    kafka_bootstrap_servers: list[str]
    kafka_raw_topic: str
    kafka_consumer_group: str
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_database: str
    model_path: Path
    legacy_model_path: Path
    champion_scaling_path: Path


settings = Settings(
    kafka_bootstrap_servers=_split_csv(
        os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    ),
    kafka_raw_topic=os.getenv("KAFKA_RAW_TOPIC", "esports_raw_events"),
    kafka_consumer_group=os.getenv(
        "KAFKA_CONSUMER_GROUP", "esports_stream_processing_v1"
    ),
    clickhouse_host=os.getenv("CLICKHOUSE_HOST", "localhost"),
    clickhouse_port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
    clickhouse_user=os.getenv("CLICKHOUSE_USER", "admin"),
    clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", "admin123"),
    clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", "esports"),
    model_path=ROOT_DIR / "machine_learning" / "models" / "win_rate_model.pkl",
    legacy_model_path=ROOT_DIR / "machine_learning" / "models" / "win_rate_model.legacy.json",
    champion_scaling_path=ROOT_DIR / "machine_learning" / "data" / "champion_scaling.json",
)
