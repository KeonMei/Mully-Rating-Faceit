import pytest

from src.analyzer import AnalysisError, analyze_player, country_flag
from src.faceit import FaceitError

from fakes import FakeClient, history_item, match_round, player_stats

PLAYER = {
    "player_id": "pid-1",
    "nickname": "Alice",
    "avatar": "https://example.com/a.png",
    "country": "kz",
    "games": {"cs2": {"faceit_elo": 2100, "skill_level": 10}},
}


def make_client(history, matches):
    responses = {
        "/players": PLAYER,
        "/players/pid-1/games/cs2/stats": {"items": history},
    }
    for match_id, players in matches.items():
        responses[f"/matches/{match_id}/stats"] = {"rounds": [match_round(players)]}
    return FakeClient(responses)


def test_report():
    client = make_client(
        history=[
            history_item("new", map_name="de_inferno", adr=60, kd=0.6),
            history_item("old", map_name="de_mirage", adr=110, kd=1.7, kr=1.0, mvps=4),
        ],
        matches={
            "new": {"pid-1": player_stats()},
            "old": {"pid-1": player_stats(entry=0.7, clutch_1v1=(2, 2), double=4)},
        },
    )

    report = analyze_player(client, "alice", 30)

    assert report.nickname == "Alice"
    assert report.flag == "🇰🇿"
    assert report.elo == 2100
    assert report.level == 10
    assert report.matches_count == 2
    assert report.matches_requested == 30
    assert 0 <= report.score <= 100
    assert report.rank.startswith(("🟣", "🔵", "🟢", "🟡", "🔴"))

    # Oldest match first, map names are kept (they used to be "Unknown").
    assert [m.map for m in report.matches] == ["de_mirage", "de_inferno"]
    assert report.matches[0].score > report.matches[1].score

    assert client.calls[1] == ("/players/pid-1/games/cs2/stats", {"limit": 30, "offset": 0})


def test_matches_without_details_are_skipped():
    client = make_client(
        history=[history_item("ok"), history_item("broken")],
        matches={"ok": {"pid-1": player_stats()}},
    )
    client.responses["/matches/broken/stats"] = FaceitError("timeout")

    report = analyze_player(client, "alice", 10)

    assert report.matches_count == 1
    assert report.matches_requested == 10


def test_player_not_found():
    client = FakeClient({"/players": None})
    with pytest.raises(AnalysisError, match="not found"):
        analyze_player(client, "nobody", 30)


def test_player_without_matches():
    client = FakeClient({"/players": PLAYER, "/players/pid-1/games/cs2/stats": {"items": []}})
    with pytest.raises(AnalysisError, match="no CS2 matches"):
        analyze_player(client, "alice", 30)


def test_all_match_details_failed():
    client = make_client(history=[history_item("m1")], matches={})
    client.responses["/matches/m1/stats"] = FaceitError("rate limited")
    with pytest.raises(FaceitError):
        analyze_player(client, "alice", 30)


def test_country_flag():
    assert country_flag("kz") == "🇰🇿"
    assert country_flag("") == ""
    assert country_flag("unknown") == ""
    assert country_flag(None) == ""
