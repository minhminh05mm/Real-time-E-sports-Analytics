import json
from datetime import datetime, timezone

from kafka import KafkaProducer


def build_producer(bootstrap_servers: list[str]) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def send_raw_message(
    producer: KafkaProducer,
    topic: str,
    message_type: str,
    match_id: str,
    payload: dict,
) -> None:
    producer.send(
        topic,
        value={
            "message_type": message_type,
            "match_id": match_id,
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        },
    )
