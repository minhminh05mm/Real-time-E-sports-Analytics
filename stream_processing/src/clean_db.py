from stream_processing.src.clickhouse_client import get_clickhouse_client


client = get_clickhouse_client()


def clean_all_data() -> None:
    tables = [
        "matches",
        "participants",
        "timeline_events",
        "match_stats_per_minute",
        "win_predictions",
    ]

    for table_name in tables:
        try:
            client.execute(f"TRUNCATE TABLE {table_name}")
            print(f"Truncated {table_name}")
        except Exception as exc:
            print(f"Failed to truncate {table_name}: {exc}")


if __name__ == "__main__":
    clean_all_data()
