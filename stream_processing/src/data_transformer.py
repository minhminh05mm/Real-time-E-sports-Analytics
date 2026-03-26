from datetime import datetime

from stream_processing.src.ai_inference import calculate_scaling_diff, predict_blue_win_rate
from stream_processing.src.config import OBJECTIVE_EVENT_TYPES, TRACKED_EVENT_TYPES


def transform_match_detail(data: dict) -> tuple[dict, list[dict], dict[int, dict]]:
    info = data["info"]
    match_id = data["metadata"]["matchId"]

    match_row = {
        "match_id": match_id,
        "game_creation": info.get("gameCreation", 0),
        "game_start_timestamp": info.get(
            "gameStartTimestamp", info.get("gameCreation", 0)
        ),
        "game_duration": info.get("gameDuration", 0),
        "game_mode": info.get("gameMode", "UNKNOWN"),
        "game_version": info.get("gameVersion", ""),
        "queue_id": info.get("queueId", 0),
        "winner_team_id": 100 if info["teams"][0]["win"] else 200,
    }

    participant_rows: list[dict] = []
    participant_lookup: dict[int, dict] = {}
    for participant in info["participants"]:
        perks = participant.get("perks", {}).get("styles", [])
        participant_row = {
            "match_id": match_id,
            "puuid": participant.get("puuid", ""),
            "summoner_name": participant.get(
                "riotIdGameName", participant.get("summonerName", "Unknown")
            ),
            "team_id": participant["teamId"],
            "participant_id": participant["participantId"],
            "champion_name": participant["championName"],
            "win": 1 if participant["win"] else 0,
            "kills": participant.get("kills", 0),
            "deaths": participant.get("deaths", 0),
            "assists": participant.get("assists", 0),
            "kda": participant.get("challenges", {}).get("kda", 0.0),
            "total_damage_dealt": participant.get("totalDamageDealtToChampions", 0),
            "physical_damage_dealt": participant.get(
                "physicalDamageDealtToChampions", 0
            ),
            "magic_damage_dealt": participant.get("magicDamageDealtToChampions", 0),
            "true_damage_dealt": participant.get("trueDamageDealtToChampions", 0),
            "total_damage_taken": participant.get("totalDamageTaken", 0),
            "physical_damage_taken": participant.get("physicalDamageTaken", 0),
            "magic_damage_taken": participant.get("magicDamageTaken", 0),
            "true_damage_taken": participant.get("trueDamageTaken", 0),
            "total_minions_killed": participant.get("totalMinionsKilled", 0),
            "gold_earned": participant.get("goldEarned", 0),
            "vision_score": participant.get("visionScore", 0),
            "wards_placed": participant.get("wardsPlaced", 0),
            "wards_killed": participant.get("wardsKilled", 0),
            "spell1_id": participant.get("summoner1Id", 0),
            "spell2_id": participant.get("summoner2Id", 0),
            "perk_primary_style": perks[0]["style"] if len(perks) > 0 else 0,
            "perk_sub_style": perks[1]["style"] if len(perks) > 1 else 0,
            "item0": participant.get("item0", 0),
            "item1": participant.get("item1", 0),
            "item2": participant.get("item2", 0),
            "item3": participant.get("item3", 0),
            "item4": participant.get("item4", 0),
            "item5": participant.get("item5", 0),
            "item6": participant.get("item6", 0),
        }
        participant_rows.append(participant_row)
        participant_lookup[participant["participantId"]] = {
            "summoner_name": participant_row["summoner_name"],
            "champion_name": participant_row["champion_name"],
            "team_id": participant_row["team_id"],
        }

    return match_row, participant_rows, participant_lookup


def transform_timeline(
    data: dict,
    participant_lookup: dict[int, dict],
    model,
    scaling_map: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    info = data["info"]
    match_id = data["metadata"]["matchId"]

    events_batch: list[dict] = []
    stats_batch: list[dict] = []
    predictions_batch: list[dict] = []
    objective_diff = 0
    scaling_diff = calculate_scaling_diff(participant_lookup, scaling_map)

    for frame in info.get("frames", []):
        minute = int(frame.get("timestamp", 0) / 60000)
        event_time = datetime.utcnow()
        participant_frames = frame.get("participantFrames", {})

        blue_gold = 0
        red_gold = 0
        blue_xp = 0
        red_xp = 0

        for event in frame.get("events", []):
            event_type = event.get("type", "")
            if event_type not in TRACKED_EVENT_TYPES:
                continue

            killer_id = event.get("killerId", 0) or event.get("creatorId", 0) or 0
            victim_id = event.get("victimId", 0)
            position = event.get("position", {"x": 0, "y": 0})
            killer_info = participant_lookup.get(killer_id, {})
            victim_info = participant_lookup.get(victim_id, {})

            if event_type in OBJECTIVE_EVENT_TYPES:
                if 1 <= killer_id <= 5:
                    objective_diff += 1
                elif 6 <= killer_id <= 10:
                    objective_diff -= 1

            events_batch.append(
                {
                    "match_id": match_id,
                    "event_time": event_time,
                    "game_timestamp": event.get("timestamp", 0),
                    "minute": minute,
                    "type": event_type,
                    "killer_id": killer_id,
                    "killer_name": killer_info.get("summoner_name", str(killer_id)),
                    "victim_id": victim_id,
                    "victim_name": victim_info.get("summoner_name", str(victim_id)),
                    "assisting_participant_ids": event.get(
                        "assistingParticipantIds", []
                    ),
                    "position_x": int(position.get("x", 0)),
                    "position_y": int(position.get("y", 0)),
                }
            )

        for participant_id in range(1, 11):
            participant_frame = participant_frames.get(str(participant_id), {})
            player_info = participant_lookup.get(participant_id, {})
            team_id = int(player_info.get("team_id", 100 if participant_id <= 5 else 200))

            total_gold = participant_frame.get("totalGold", 0)
            xp = participant_frame.get("xp", 0)
            if team_id == 100:
                blue_gold += total_gold
                blue_xp += xp
            else:
                red_gold += total_gold
                red_xp += xp

            stats_batch.append(
                {
                    "match_id": match_id,
                    "minute": minute,
                    "participant_id": participant_id,
                    "team_id": team_id,
                    "champion_name": player_info.get("champion_name", "Unknown"),
                    "current_gold": participant_frame.get("currentGold", 0),
                    "total_gold": total_gold,
                    "xp": xp,
                    "level": participant_frame.get("level", 1),
                    "damage_done_to_champs": participant_frame.get("damageStats", {}).get(
                        "totalDamageDoneToChampions", 0
                    ),
                    "minions_killed": participant_frame.get("minionsKilled", 0),
                    "jungle_minions_killed": participant_frame.get(
                        "jungleMinionsKilled", 0
                    ),
                    "position_x": int(participant_frame.get("position", {}).get("x", 0)),
                    "position_y": int(participant_frame.get("position", {}).get("y", 0)),
                }
            )

        feature_row = {
            "minute": minute,
            "gold_diff": blue_gold - red_gold,
            "xp_diff": blue_xp - red_xp,
            "obj_diff": objective_diff,
            "scaling_diff": scaling_diff,
        }
        blue_win_rate = predict_blue_win_rate(model, feature_row)
        predictions_batch.append(
            {
                "match_id": match_id,
                "minute": minute,
                "predicted_win_rate_blue": blue_win_rate,
                "predicted_winner_team_id": 100 if blue_win_rate >= 50.0 else 200,
                "gold_diff": feature_row["gold_diff"],
                "xp_diff": feature_row["xp_diff"],
                "obj_diff": feature_row["obj_diff"],
                "scaling_diff": feature_row["scaling_diff"],
                "generated_at": event_time,
            }
        )

    return events_batch, stats_batch, predictions_batch
