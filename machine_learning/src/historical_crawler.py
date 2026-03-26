import argparse
import json
import time

from riotwatcher import ApiError, LolWatcher

from machine_learning.src.config import RAW_MATCHES_DIR, RAW_TIMELINES_DIR, settings


QUEUE_ID_RANKED_SOLO = 420
watcher = LolWatcher(settings.riot_api_key) if settings.riot_api_key else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl ranked solo matches without duplicate match IDs."
    )
    parser.add_argument(
        "--tier",
        default=settings.target_tier,
        choices=["CHALLENGER", "GRANDMASTER", "MASTER"],
        help="Rank tier to crawl.",
    )
    parser.add_argument(
        "--target-match-count",
        type=int,
        default=settings.target_match_count,
        help="Stop after storing this many unique matches.",
    )
    parser.add_argument(
        "--matches-per-player",
        type=int,
        default=settings.matches_per_player,
        help="How many recent matches to request per player.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.2,
        help="Delay between successful match fetches.",
    )
    return parser


def get_rank_players(tier: str) -> list[dict]:
    if watcher is None:
        raise RuntimeError("RIOT_API_KEY is missing in .env")

    tier = tier.upper()
    if tier == "CHALLENGER":
        league = watcher.league.challenger_by_queue(settings.riot_region, "RANKED_SOLO_5x5")
    elif tier == "GRANDMASTER":
        league = watcher.league.grandmaster_by_queue(
            settings.riot_region, "RANKED_SOLO_5x5"
        )
    else:
        league = watcher.league.masters_by_queue(settings.riot_region, "RANKED_SOLO_5x5")
    return sorted(league["entries"], key=lambda row: row["leaguePoints"], reverse=True)


def get_puuid(player: dict) -> str | None:
    if watcher is None:
        return None

    if "puuid" in player:
        return player["puuid"]
    if "summonerId" not in player:
        return None

    try:
        return watcher.summoner.by_id(settings.riot_region, player["summonerId"])["puuid"]
    except ApiError as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code == 429:
            retry_after = int(exc.response.headers.get("Retry-After", "10"))
            print(f"Summoner API rate limited. Sleeping {retry_after}s")
            time.sleep(retry_after)
            return get_puuid(player)
        return None


def load_existing_match_ids() -> set[str]:
    RAW_MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    RAW_TIMELINES_DIR.mkdir(parents=True, exist_ok=True)

    match_ids = {path.stem for path in RAW_MATCHES_DIR.glob("*.json")}
    match_ids.update(path.stem for path in RAW_TIMELINES_DIR.glob("*.json"))
    return match_ids


def persist_match_bundle(match_id: str, match_detail: dict, timeline: dict) -> None:
    RAW_MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    RAW_TIMELINES_DIR.mkdir(parents=True, exist_ok=True)

    with (RAW_MATCHES_DIR / f"{match_id}.json").open("w", encoding="utf-8") as file_handle:
        json.dump(match_detail, file_handle, ensure_ascii=False)

    with (RAW_TIMELINES_DIR / f"{match_id}.json").open("w", encoding="utf-8") as file_handle:
        json.dump(timeline, file_handle, ensure_ascii=False)


def fetch_ranked_match_ids(puuid: str, matches_per_player: int) -> list[str]:
    if watcher is None:
        return []

    try:
        return watcher.match.matchlist_by_puuid(
            settings.riot_routing,
            puuid,
            count=matches_per_player,
            queue=QUEUE_ID_RANKED_SOLO,
        )
    except ApiError as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code == 429:
            retry_after = int(exc.response.headers.get("Retry-After", "10"))
            print(f"Matchlist API rate limited. Sleeping {retry_after}s")
            time.sleep(retry_after)
            return fetch_ranked_match_ids(puuid, matches_per_player)
        return []


def run_historical_crawler(
    tier: str,
    target_match_count: int,
    matches_per_player: int,
    delay_seconds: float,
) -> None:
    if watcher is None:
        raise RuntimeError("RIOT_API_KEY is missing in .env")

    players = get_rank_players(tier)
    seen_match_ids = load_existing_match_ids()
    crawled_count = 0
    skipped_duplicates = 0

    print(
        f"Loaded {len(players)} players from tier={tier}. "
        f"Existing unique matches on disk: {len(seen_match_ids)}"
    )

    for index, player in enumerate(players, start=1):
        if crawled_count >= target_match_count:
            break

        puuid = get_puuid(player)
        if not puuid:
            continue

        player_name = player.get("summonerName", player.get("leaguePoints", "unknown"))
        print(f"\n[{index}/{len(players)}] Crawling player: {player_name}")

        match_ids = fetch_ranked_match_ids(puuid, matches_per_player)
        if not match_ids:
            continue

        for match_id in match_ids:
            if crawled_count >= target_match_count:
                break

            if match_id in seen_match_ids:
                skipped_duplicates += 1
                continue

            try:
                match_detail = watcher.match.by_id(settings.riot_routing, match_id)
                if match_detail["info"].get("queueId") != QUEUE_ID_RANKED_SOLO:
                    continue
                timeline = watcher.match.timeline_by_match(settings.riot_routing, match_id)
                timeline.setdefault("metadata", {})["matchId"] = match_id
            except ApiError as exc:
                status_code = getattr(exc.response, "status_code", None)
                if status_code == 429:
                    retry_after = int(exc.response.headers.get("Retry-After", "30"))
                    print(f"Match API rate limited for {match_id}. Sleeping {retry_after}s")
                    time.sleep(retry_after)
                continue

            persist_match_bundle(match_id, match_detail, timeline)
            seen_match_ids.add(match_id)
            crawled_count += 1
            print(
                f"Stored unique match {match_id} "
                f"({crawled_count}/{target_match_count})"
            )
            time.sleep(delay_seconds)

    print(
        "\nHistorical crawl completed. "
        f"Stored {crawled_count} new unique matches, skipped {skipped_duplicates} duplicates."
    )


def main() -> None:
    args = build_parser().parse_args()
    run_historical_crawler(
        tier=args.tier,
        target_match_count=args.target_match_count,
        matches_per_player=args.matches_per_player,
        delay_seconds=args.delay_seconds,
    )


if __name__ == "__main__":
    main()
