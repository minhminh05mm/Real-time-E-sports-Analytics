import argparse
import time

from data_ingestion.src.config import QUEUE_ID_RANKED_SOLO, settings
from data_ingestion.src.kafka_producer import build_producer, send_raw_message
from data_ingestion.src.riot_api_client import RiotAPIClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish ranked solo matches to Kafka without duplicate match IDs."
    )
    parser.add_argument(
        "--tier",
        default=settings.target_tier,
        choices=["CHALLENGER", "GRANDMASTER", "MASTER"],
        help="Rank tier to ingest.",
    )
    parser.add_argument(
        "--target-match-count",
        type=int,
        default=settings.target_match_count,
        help="Stop after publishing this many unique matches.",
    )
    parser.add_argument(
        "--matches-per-player",
        type=int,
        default=settings.matches_per_player,
        help="How many recent ranked matches to request per player.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=settings.artificial_delay_seconds,
        help="Delay between published matches to simulate real-time streaming.",
    )
    return parser


def run_ingestion(
    tier: str,
    target_match_count: int,
    matches_per_player: int,
    delay_seconds: float,
) -> None:
    if not settings.riot_api_key:
        raise RuntimeError("RIOT_API_KEY is missing in .env")

    api_client = RiotAPIClient(
        api_key=settings.riot_api_key,
        region=settings.riot_region,
        routing=settings.riot_routing,
    )
    producer = build_producer(settings.kafka_bootstrap_servers)
    players = api_client.get_rank_players(tier)
    seen_match_ids: set[str] = set()
    published_count = 0
    skipped_duplicates = 0

    print(
        f"Starting real-time ingestion for tier={tier}, topic={settings.kafka_raw_topic}, "
        f"players={len(players)}"
    )

    for index, player in enumerate(players, start=1):
        if published_count >= target_match_count:
            break

        puuid = api_client.get_player_puuid(player)
        if not puuid:
            continue

        player_name = player.get("summonerName", "unknown")
        print(f"\n[{index}/{len(players)}] Streaming matches for {player_name}")

        match_ids = api_client.get_ranked_match_ids(
            puuid=puuid,
            count=matches_per_player,
            queue=QUEUE_ID_RANKED_SOLO,
        )

        for match_id in match_ids:
            if published_count >= target_match_count:
                break

            if match_id in seen_match_ids:
                skipped_duplicates += 1
                continue

            try:
                match_detail, timeline = api_client.fetch_match_bundle(match_id)
            except Exception as exc:
                print(f"Failed to fetch {match_id}: {exc}")
                continue

            if match_detail.get("info", {}).get("queueId") != QUEUE_ID_RANKED_SOLO:
                continue

            send_raw_message(
                producer,
                topic=settings.kafka_raw_topic,
                message_type="match_detail",
                match_id=match_id,
                payload=match_detail,
            )
            send_raw_message(
                producer,
                topic=settings.kafka_raw_topic,
                message_type="timeline",
                match_id=match_id,
                payload=timeline,
            )

            seen_match_ids.add(match_id)
            published_count += 1
            print(
                f"Published unique match {match_id} "
                f"({published_count}/{target_match_count})"
            )
            time.sleep(delay_seconds)

    producer.flush()
    print(
        "\nIngestion completed. "
        f"Published {published_count} unique matches and skipped {skipped_duplicates} duplicates."
    )


def main() -> None:
    args = build_parser().parse_args()
    run_ingestion(
        tier=args.tier,
        target_match_count=args.target_match_count,
        matches_per_player=args.matches_per_player,
        delay_seconds=args.delay_seconds,
    )


if __name__ == "__main__":
    main()
