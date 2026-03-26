CREATE DATABASE IF NOT EXISTS esports;

CREATE TABLE IF NOT EXISTS esports.matches (
    match_id String,
    game_creation UInt64,
    game_start_timestamp UInt64,
    game_duration UInt32,
    game_mode String,
    game_version String,
    queue_id UInt16,
    winner_team_id UInt16
) ENGINE = MergeTree()
ORDER BY (game_start_timestamp, match_id);

CREATE TABLE IF NOT EXISTS esports.participants (
    match_id String,
    puuid String,
    summoner_name String,
    team_id UInt16,
    participant_id UInt8,
    champion_name String,
    win UInt8,
    kills UInt16,
    deaths UInt16,
    assists UInt16,
    kda Float32,
    total_damage_dealt UInt32,
    physical_damage_dealt UInt32,
    magic_damage_dealt UInt32,
    true_damage_dealt UInt32,
    total_damage_taken UInt32,
    physical_damage_taken UInt32,
    magic_damage_taken UInt32,
    true_damage_taken UInt32,
    total_minions_killed UInt16,
    gold_earned UInt32,
    vision_score UInt16,
    wards_placed UInt16,
    wards_killed UInt16,
    spell1_id UInt32,
    spell2_id UInt32,
    perk_primary_style UInt32,
    perk_sub_style UInt32,
    item0 UInt32,
    item1 UInt32,
    item2 UInt32,
    item3 UInt32,
    item4 UInt32,
    item5 UInt32,
    item6 UInt32
) ENGINE = MergeTree()
ORDER BY (match_id, team_id, participant_id);

CREATE TABLE IF NOT EXISTS esports.timeline_events (
    match_id String,
    event_time DateTime,
    game_timestamp UInt32,
    minute UInt8,
    type String,
    killer_id UInt8,
    killer_name String,
    victim_id UInt8,
    victim_name String,
    assisting_participant_ids Array(UInt8),
    position_x UInt16,
    position_y UInt16
) ENGINE = MergeTree()
ORDER BY (match_id, event_time);

CREATE TABLE IF NOT EXISTS esports.match_stats_per_minute (
    match_id String,
    minute UInt8,
    participant_id UInt8,
    team_id UInt16,
    champion_name String,
    current_gold UInt32,
    total_gold UInt32,
    xp UInt32,
    level UInt8,
    damage_done_to_champs UInt32,
    minions_killed UInt16,
    jungle_minions_killed UInt16,
    position_x UInt16,
    position_y UInt16
) ENGINE = MergeTree()
ORDER BY (match_id, minute, team_id, participant_id);

CREATE TABLE IF NOT EXISTS esports.win_predictions (
    match_id String,
    minute UInt8,
    predicted_win_rate_blue Float32,
    predicted_winner_team_id UInt16,
    gold_diff Int32,
    xp_diff Int32,
    obj_diff Int16,
    scaling_diff Int16,
    generated_at DateTime
) ENGINE = MergeTree()
ORDER BY (match_id, minute, generated_at);
