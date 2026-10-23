"""Fake FACEIT data for tests."""


def player_stats(entry=0.5, clutch_1v1=(0, 0), double=0, triple=0, quadra=0, ace=0):
    """FACEIT-like player_stats (FACEIT sends numbers as strings)."""
    attempts, wins = clutch_1v1
    return {
        "Match Entry Success Rate": str(entry),
        "1v1Count": str(attempts),
        "1v1Wins": str(wins),
        "Double Kills": str(double),
        "Triple Kills": str(triple),
        "Quadro Kills": str(quadra),
        "Penta Kills": str(ace),
    }


def match_round(players, rounds=24, number="1", map_name="de_mirage"):
    """One map of /matches/{id}/stats. `players` is {player_id: player_stats}."""
    return {
        "match_round": number,
        "round_stats": {"Rounds": str(rounds), "Map": map_name},
        "teams": [
            {"players": [{"player_id": pid, "player_stats": stats}]}
            for pid, stats in players.items()
        ],
    }


def history_item(match_id, map_name="de_mirage", adr=80, kd=1.0, kr=0.7, mvps=2, number="1"):
    """One item of /players/{id}/games/cs2/stats."""
    return {"stats": {
        "Match Id": match_id,
        "Match Round": number,
        "Map": map_name,
        "ADR": str(adr),
        "K/D Ratio": str(kd),
        "K/R Ratio": str(kr),
        "MVPs": str(mvps),
    }}


class FakeClient:
    """Stands in for FaceitClient: answers from a dict of path -> JSON."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        response = self.responses.get(path)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(params)
        return response
