import json

from kafka import KafkaConsumer

from stream_processing.src.ai_inference import load_model, load_scaling_map
from stream_processing.src.clickhouse_client import get_clickhouse_client, insert_rows
from stream_processing.src.config import settings
from stream_processing.src.data_transformer import (
    transform_match_detail,
    transform_timeline,
)


def build_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        settings.kafka_raw_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id=settings.kafka_consumer_group,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def run_consumer() -> None:
    client = get_clickhouse_client()
    consumer = build_consumer()
    model = load_model()
    scaling_map = load_scaling_map()
    participant_cache: dict[str, dict[int, dict]] = {}

    print(
        f"Listening to Kafka topic={settings.kafka_raw_topic} "
        f"group_id={settings.kafka_consumer_group}"
    )

    for message in consumer:
        envelope = message.value
        message_type = envelope.get("message_type")
        payload = envelope.get("payload", envelope)
        match_id = envelope.get("match_id") or payload.get("metadata", {}).get("matchId")

        try:
            if message_type == "match_detail":
                match_row, participant_rows, participant_lookup = transform_match_detail(
                    payload
                )
                insert_rows(client, "matches", [match_row])
                insert_rows(client, "participants", participant_rows)
                if match_id:
                    participant_cache[match_id] = participant_lookup
                print(f"Processed match detail for {match_id}")

            elif message_type == "timeline":
                participant_lookup = participant_cache.get(match_id or "", {})
                events_batch, stats_batch, predictions_batch = transform_timeline(
                    payload,
                    participant_lookup,
                    model,
                    scaling_map,
                )
                insert_rows(client, "timeline_events", events_batch)
                insert_rows(client, "match_stats_per_minute", stats_batch)
                insert_rows(client, "win_predictions", predictions_batch)
                print(f"Processed timeline for {match_id}")

            else:
                print(f"Skipping unsupported message type: {message_type}")
        except Exception as exc:
            print(f"Failed to process message for {match_id}: {exc}")


if __name__ == "__main__":
    run_consumer()
