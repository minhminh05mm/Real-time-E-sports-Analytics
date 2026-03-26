import time
from urllib.parse import quote

import requests
from riotwatcher import ApiError, LolWatcher


class RiotAPIClient:
    def __init__(self, api_key: str, region: str, routing: str) -> None:
        self.api_key = api_key
        self.region = region
        self.routing = routing
        self.watcher = LolWatcher(api_key)

    def get_puuid(self, game_name: str, tag_line: str) -> str | None:
        safe_name = quote(game_name)
        safe_tag = quote(tag_line)
        url = (
            f"https://{self.routing}.api.riotgames.com/riot/account/v1/accounts/"
            f"by-riot-id/{safe_name}/{safe_tag}"
        )
        headers = {"X-Riot-Token": self.api_key}

        try:
            response = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as exc:
            print(f"Account API request failed for {game_name}#{tag_line}: {exc}")
            return None

        if response.status_code == 200:
            return response.json()["puuid"]
        if response.status_code == 404:
            print(f"Player not found: {game_name}#{tag_line}")
            return None
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "10"))
            print(f"Account API rate limited. Sleeping {retry_after}s")
            time.sleep(retry_after)
            return self.get_puuid(game_name, tag_line)

        print(f"Account API failed ({response.status_code}): {response.text}")
        return None

    def get_recent_matches(self, puuid: str, count: int = 5) -> list[str]:
        try:
            return self.watcher.match.matchlist_by_puuid(self.routing, puuid, count=count)
        except ApiError as exc:
            print(f"Failed to fetch recent matches: {exc}")
            return []

    def get_rank_players(self, tier: str) -> list[dict]:
        tier = tier.upper()
        if tier == "CHALLENGER":
            league = self.watcher.league.challenger_by_queue(
                self.region, "RANKED_SOLO_5x5"
            )
        elif tier == "GRANDMASTER":
            league = self.watcher.league.grandmaster_by_queue(
                self.region, "RANKED_SOLO_5x5"
            )
        else:
            league = self.watcher.league.masters_by_queue(
                self.region, "RANKED_SOLO_5x5"
            )
        return sorted(league["entries"], key=lambda row: row["leaguePoints"], reverse=True)

    def get_player_puuid(self, player: dict) -> str | None:
        if "puuid" in player:
            return player["puuid"]
        if "summonerId" not in player:
            return None

        try:
            return self.watcher.summoner.by_id(self.region, player["summonerId"])["puuid"]
        except ApiError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code == 429:
                retry_after = int(exc.response.headers.get("Retry-After", "10"))
                print(f"Summoner API rate limited. Sleeping {retry_after}s")
                time.sleep(retry_after)
                return self.get_player_puuid(player)
            return None

    def get_ranked_match_ids(self, puuid: str, count: int, queue: int = 420) -> list[str]:
        try:
            return self.watcher.match.matchlist_by_puuid(
                self.routing,
                puuid,
                count=count,
                queue=queue,
            )
        except ApiError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code == 429:
                retry_after = int(exc.response.headers.get("Retry-After", "10"))
                print(f"Matchlist API rate limited. Sleeping {retry_after}s")
                time.sleep(retry_after)
                return self.get_ranked_match_ids(puuid, count=count, queue=queue)
            print(f"Failed to fetch ranked match ids: {exc}")
            return []

    def fetch_match_bundle(self, match_id: str) -> tuple[dict, dict]:
        try:
            match_detail = self.watcher.match.by_id(self.routing, match_id)
            timeline = self.watcher.match.timeline_by_match(self.routing, match_id)
            timeline.setdefault("metadata", {})["matchId"] = match_id
            return match_detail, timeline
        except ApiError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code == 429:
                retry_after = int(exc.response.headers.get("Retry-After", "30"))
                print(f"Match API rate limited for {match_id}. Sleeping {retry_after}s")
                time.sleep(retry_after)
                return self.fetch_match_bundle(match_id)
            raise
