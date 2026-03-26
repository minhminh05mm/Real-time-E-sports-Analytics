import json

import pandas as pd

from machine_learning.src.config import (
    CHAMPION_SCALING_PATH,
    TRAINING_DATA_PATH,
    get_clickhouse_client,
)


client = get_clickhouse_client()


def load_champion_scaling() -> dict:
    if not CHAMPION_SCALING_PATH.exists():
        print(f"Champion scaling file not found: {CHAMPION_SCALING_PATH}")
        return {}

    with CHAMPION_SCALING_PATH.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


CHAMPION_SCALING_MAP = load_champion_scaling()


def get_scaling_score(champion_name: str | None) -> int:
    if not champion_name:
        return 5

    clean_name_db = champion_name.replace(" ", "").replace("'", "").replace(".", "").lower()
    for json_key, score in CHAMPION_SCALING_MAP.items():
        if json_key == "_COMMENT":
            continue
        clean_name_json = json_key.replace(" ", "").replace("'", "").replace(".", "").lower()
        if clean_name_db == clean_name_json:
            return score
    return 5


def extract_data_to_csv() -> None:
    print("Extracting training features from ClickHouse")

    sql_stats = """
    SELECT
        s.match_id, s.minute, s.team_id, p.champion_name,
        s.total_gold, s.xp, s.damage_done_to_champs,
        if(m.winner_team_id = 100, 1, 0) AS label
    FROM esports.match_stats_per_minute AS s
    JOIN esports.participants AS p
      ON s.match_id = p.match_id AND s.participant_id = p.participant_id
    JOIN esports.matches AS m
      ON s.match_id = m.match_id
    ORDER BY s.match_id, s.minute
    """
    stats_data = client.execute(sql_stats)
    df_stats = pd.DataFrame(
        stats_data,
        columns=["match_id", "minute", "team_id", "champion", "gold", "xp", "dmg", "label"],
    )

    if df_stats.empty:
        print("No data available in ClickHouse")
        return

    sql_events = """
    SELECT match_id, minute, type, killer_id
    FROM esports.timeline_events
    WHERE type IN ('ELITE_MONSTER_KILL', 'BUILDING_KILL', 'TURRET_PLATE_DESTROYED')
    """
    events_data = client.execute(sql_events)
    df_events = pd.DataFrame(events_data, columns=["match_id", "minute", "type", "killer_id"])

    df_pivot = (
        df_stats.pivot_table(
            index=["match_id", "minute"],
            columns="team_id",
            values=["gold", "xp"],
            aggfunc="sum",
        )
        .fillna(0)
    )
    df_pivot.columns = [f"{column[0]}_{column[1]}" for column in df_pivot.columns]
    df_pivot["gold_diff"] = df_pivot["gold_100"] - df_pivot["gold_200"]
    df_pivot["xp_diff"] = df_pivot["xp_100"] - df_pivot["xp_200"]

    match_labels = df_stats[["match_id", "label"]].drop_duplicates().set_index("match_id")
    df_result = df_pivot.join(match_labels)

    if not df_events.empty:
        df_events["obj_point"] = df_events["killer_id"].apply(
            lambda value: 1 if 1 <= value <= 5 else (-1 if 6 <= value <= 10 else 0)
        )
        obj_per_min = df_events.groupby(["match_id", "minute"])["obj_point"].sum().reset_index()
        obj_per_min["obj_diff"] = obj_per_min.groupby("match_id")["obj_point"].cumsum()
        df_result = df_result.join(
            obj_per_min.set_index(["match_id", "minute"]),
            on=["match_id", "minute"],
        )
        df_result["obj_diff"] = df_result.groupby("match_id")["obj_diff"].ffill().fillna(0)
    else:
        df_result["obj_diff"] = 0

    scaling_rows = []
    unique_matches = df_stats[["match_id", "team_id", "champion"]].drop_duplicates()
    for match_id, group in unique_matches.groupby("match_id"):
        blue_champs = group[group["team_id"] == 100]["champion"].values
        red_champs = group[group["team_id"] == 200]["champion"].values
        scaling_rows.append(
            {
                "match_id": match_id,
                "scaling_diff": sum(get_scaling_score(name) for name in blue_champs)
                - sum(get_scaling_score(name) for name in red_champs),
            }
        )

    df_scaling = pd.DataFrame(scaling_rows).set_index("match_id")
    df_final = df_result.join(df_scaling, on="match_id").reset_index()
    df_final = df_final[
        ["match_id", "minute", "gold_diff", "xp_diff", "obj_diff", "scaling_diff", "label"]
    ]

    TRAINING_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(TRAINING_DATA_PATH, index=False)
    print(f"Saved {len(df_final)} rows to {TRAINING_DATA_PATH}")


if __name__ == "__main__":
    extract_data_to_csv()
