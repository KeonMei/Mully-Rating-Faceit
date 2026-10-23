from mully_rating.faceit.client import FaceitError
from mully_rating.faceit.matches import Duels, analyze_match

from fakes import FakeClient, match_round, player_stats


def test_two_players_from_same_match_get_their_own_stats():
    # Regression: the cache was keyed by match_id only, so the second
    # player got the stats of the first one.
    client = FakeClient({"/matches/m1/stats": {"rounds": [match_round({
        "alice": player_stats(entry=0.8, clutch_1v1=(4, 1), double=5),
        "bob": player_stats(entry=0.1),
    })]}})

    alice = analyze_match(client, "m1", "alice")
    bob = analyze_match(client, "m1", "bob")

    assert alice["entry_success"] == 0.8
    assert alice["clutches"]["1v1"].attempts == 4
    assert alice["clutches"]["1v1"].wins == 1
    assert alice["double"] == 5
    assert alice["rounds"] == 24

    assert bob["entry_success"] == 0.1
    assert bob["double"] == 0

    # The second lookup came from the cache.
    assert len(client.calls) == 1


def test_player_not_in_match():
    client = FakeClient({"/matches/m1/stats": {"rounds": [match_round({"alice": player_stats()})]}})
    assert analyze_match(client, "m1", "carol") is None


def test_picks_the_right_map_of_a_bo3():
    client = FakeClient({"/matches/bo3/stats": {"rounds": [
        match_round({"alice": player_stats(double=1)}, number="1"),
        match_round({"alice": player_stats(double=2)}, number="2"),
        match_round({"alice": player_stats(double=3)}, number="3"),
    ]}})

    assert analyze_match(client, "bo3", "alice", "2")["double"] == 2
    assert analyze_match(client, "bo3", "alice", "3")["double"] == 3
    assert analyze_match(client, "bo3", "alice")["double"] == 1


def test_failed_requests_are_not_cached():
    client = FakeClient({"/matches/m1/stats": FaceitError("down")})
    assert analyze_match(client, "m1", "alice") is None

    client.responses["/matches/m1/stats"] = {"rounds": [match_round({"alice": player_stats()})]}
    assert analyze_match(client, "m1", "alice") is not None


def test_bad_numbers_become_zero():
    stats = player_stats()
    stats["Double Kills"] = ""
    stats["Match Entry Success Rate"] = None
    client = FakeClient({"/matches/m1/stats": {"rounds": [match_round({"alice": stats})]}})

    result = analyze_match(client, "m1", "alice")

    assert result["double"] == 0
    assert result["entry_success"] == 0


def test_entry_duels_are_read_when_present():
    client = FakeClient({"/matches/m1/stats": {"rounds": [match_round({
        "alice": player_stats(entry=0.75, entry_duels=(4, 3)),
        "bob": player_stats(entry=0.5),
    })]}})

    alice = analyze_match(client, "m1", "alice")
    bob = analyze_match(client, "m1", "bob")

    assert alice["entry"] == Duels(attempts=4, wins=3)
    assert alice["entry_success"] == 0.75
    assert bob["entry"] is None  # FACEIT sent only the rate
    assert bob["entry_success"] == 0.5
