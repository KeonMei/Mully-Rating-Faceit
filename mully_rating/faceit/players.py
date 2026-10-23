"""Player profile and match history from FACEIT."""

from dataclasses import dataclass

from mully_rating.faceit.client import to_float

# FACEIT does not return more than 100 matches per request.
MAX_MATCHES = 100


@dataclass
class Player:
    player_id: str
    nickname: str
    avatar: str | None
    elo: int | str
    level: int | str
    country: str


def get_player_info(client, nickname):
    """Look up a player by nickname. Returns Player or None if not found."""

    data = client.get("/players", {"nickname": nickname})

    if not data or "player_id" not in data:
        return None

    avatar = (data.get("avatar") or "").strip()

    if not avatar.startswith("http"):
        avatar = None

    cs2 = data.get("games", {}).get("cs2", {})

    return Player(
        player_id=data["player_id"],
        nickname=data.get("nickname") or nickname,
        avatar=avatar,
        elo=cs2.get("faceit_elo", "N/A"),
        level=cs2.get("skill_level", "N/A"),
        country=data.get("country", ""),
    )


def get_matches(client, player_id, limit=30):
    """Basic stats of the player's last `limit` CS2 matches, newest first."""

    limit = max(1, min(limit, MAX_MATCHES))

    data = client.get(
        f"/players/{player_id}/games/cs2/stats",
        {"limit": limit, "offset": 0}
    )

    if not data:
        return []

    matches = []

    for item in data.get("items", []):

        stats = item.get("stats", {})

        match_id = stats.get("Match Id")

        if not match_id:
            continue

        matches.append({
            "match_id": match_id,
            # Map number inside a BO3 series ("1", "2", ...).
            "match_round": stats.get("Match Round"),
            "map": (
                stats.get("Map")
                or stats.get("Map Name")
                or stats.get("Game Map")
                or "Unknown"
            ),
            "ADR": to_float(stats.get("ADR")),
            "KD": to_float(stats.get("K/D Ratio")),
            "KR": to_float(stats.get("K/R Ratio")),
            "MVPs": to_float(stats.get("MVPs")),
        })

    return matches
