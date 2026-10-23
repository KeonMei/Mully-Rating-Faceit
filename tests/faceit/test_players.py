from mully_rating.faceit.players import get_matches, get_player_info

from fakes import FakeClient, history_item


def test_player_info():
    client = FakeClient({"/players": {
        "player_id": "pid",
        "nickname": "Alice",
        "avatar": " https://example.com/a.png ",
        "country": "kz",
        "games": {"cs2": {"faceit_elo": 2100, "skill_level": 10}},
    }})

    player = get_player_info(client, "alice")

    assert player.player_id == "pid"
    assert player.nickname == "Alice"
    assert player.avatar == "https://example.com/a.png"
    assert (player.elo, player.level, player.country) == (2100, 10, "kz")
    assert client.calls == [("/players", {"nickname": "alice"})]


def test_player_without_avatar_or_cs2():
    client = FakeClient({"/players": {"player_id": "pid", "avatar": ""}})

    player = get_player_info(client, "bob")

    assert player.nickname == "bob"
    assert player.avatar is None
    assert player.elo == "N/A"


def test_player_not_found():
    assert get_player_info(FakeClient({"/players": None}), "nobody") is None


def test_matches():
    no_id = {"stats": {"Map": "de_nuke"}}
    client = FakeClient({"/players/pid/games/cs2/stats": {"items": [
        history_item("m1", map_name="de_mirage", adr=91.5, kd=1.25, number="2", kills=25, deaths=20),
        no_id,
    ]}})

    matches = get_matches(client, "pid", limit=500)

    assert client.calls == [("/players/pid/games/cs2/stats", {"limit": 100, "offset": 0})]
    assert len(matches) == 1
    assert matches[0]["match_id"] == "m1"
    assert matches[0]["map"] == "de_mirage"
    assert matches[0]["match_round"] == "2"
    assert matches[0]["ADR"] == 91.5
    assert matches[0]["KD"] == 1.25
    assert (matches[0]["kills"], matches[0]["deaths"]) == (25, 20)


def test_no_matches():
    assert get_matches(FakeClient({}), "pid") == []
