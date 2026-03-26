from stream_processing.src.clickhouse_client import get_clickhouse_client


client = get_clickhouse_client()


def check_tables() -> None:
    print("\nClickHouse validation")
    print("-" * 60)

    counts = {
        "matches": client.execute("SELECT count() FROM matches")[0][0],
        "participants": client.execute("SELECT count() FROM participants")[0][0],
        "timeline_events": client.execute("SELECT count() FROM timeline_events")[0][0],
        "match_stats_per_minute": client.execute(
            "SELECT count() FROM match_stats_per_minute"
        )[0][0],
        "win_predictions": client.execute("SELECT count() FROM win_predictions")[0][0],
    }

    for table_name, row_count in counts.items():
        print(f"{table_name:<24}: {row_count}")

    if counts["matches"] == 0:
        print("No match data found yet.")
        return

    sample_sql = """
    SELECT
        match_id,
        minute,
        predicted_win_rate_blue,
        gold_diff,
        xp_diff,
        obj_diff
    FROM win_predictions
    ORDER BY match_id, minute
    LIMIT 10
    """
    sample_rows = client.execute(sample_sql)
    if not sample_rows:
        print("No prediction rows available yet.")
        return

    print("\nSample predictions")
    print(f"{'Match ID':<16} {'Min':<4} {'Blue WR':<10} {'Gold':<8} {'XP':<8} {'Obj':<6}")
    print("-" * 60)
    for row in sample_rows:
        print(
            f"{row[0][:14] + '..':<16} {row[1]:<4} {row[2]:<10.2f} "
            f"{row[3]:<8} {row[4]:<8} {row[5]:<6}"
        )


if __name__ == "__main__":
    check_tables()
