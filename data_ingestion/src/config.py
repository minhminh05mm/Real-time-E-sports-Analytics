import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

QUEUE_ID_RANKED_SOLO = 420


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    riot_api_key: str
    riot_region: str
    riot_routing: str
    kafka_bootstrap_servers: list[str]
    kafka_raw_topic: str
    target_tier: str
    target_match_count: int
    matches_per_player: int
    artificial_delay_seconds: float


settings = Settings(
    riot_api_key=os.getenv("RIOT_API_KEY", ""),
    riot_region=os.getenv("RIOT_REGION", "kr"),
    riot_routing=os.getenv("RIOT_ROUTING", "asia"),
    kafka_bootstrap_servers=_split_csv(
        os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    ),
    kafka_raw_topic=os.getenv("KAFKA_RAW_TOPIC", "esports_raw_events"),
    target_tier=os.getenv("INGEST_TARGET_TIER", "CHALLENGER"),
    target_match_count=int(os.getenv("INGEST_TARGET_MATCH_COUNT", "50")),
    matches_per_player=int(os.getenv("INGEST_MATCHES_PER_PLAYER", "25")),
    artificial_delay_seconds=float(
        os.getenv("INGEST_ARTIFICIAL_DELAY_SECONDS", "1.5")
    ),
)
