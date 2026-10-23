import pytest

from mully_rating.analyzer import AnalysisError, analyze_player, country_flag
from mully_rating.faceit.client import FaceitError

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


def test_report_has_breakdown_and_totals_based_kd():
    client = make_client(
        history=[
            history_item("m1", kd=3.0, kills=30, deaths=10),
            history_item("m2", kd=0.5, kills=10, deaths=20),
        ],
        matches={
            "m1": {"pid-1": player_stats(entry_duels=(4, 3))},
            "m2": {"pid-1": player_stats(entry_duels=(2, 0))},
        },
    )

    report = analyze_player(client, "alice", 10)

    assert set(report.components) == {"combat", "multi", "entry", "clutch"}
    assert all(0 <= value <= 100 for value in report.components.values())
    assert report.stats["kd"] == pytest.approx(40 / 30)
    # 3 of 6 opening duels won plus 4 imaginary average duels.
    assert report.stats["entry"] == pytest.approx(0.5)
    assert all(match.totals is not None for match in report.matches)
