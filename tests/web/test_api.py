import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from mully_rating.faceit.client import FaceitError
from mully_rating.web import api

from fakes import FakeClient, history_item, match_round, player_stats

PLAYER = {
    "player_id": "pid",
    "nickname": "Alice",
    "avatar": "https://example.com/a.png",
    "country": "kz",
    "games": {"cs2": {"faceit_elo": 2100, "skill_level": 10}},
}


def faceit(history=None):
    history = history if history is not None else [
        history_item("m1", "de_inferno", adr=60, kd=0.6, kills=9, deaths=15),
        history_item("m2", "de_mirage", adr=110, kd=1.7, kills=34, deaths=20),
    ]
    responses = {
        "/players": lambda params: PLAYER if params["nickname"].lower() == "alice" else None,
        "/players/pid/games/cs2/stats": {"items": history},
    }
    for item in history:
        match_id = item["stats"]["Match Id"]
        responses[f"/matches/{match_id}/stats"] = {"rounds": [match_round({"pid": player_stats(double=3)})]}
    return FakeClient(responses)


def query(**params):
    return {key: [value] for key, value in params.items()}


def test_rating_json():
    status, body, cache = api.rating_response(faceit(), query(player="alice", matches="10"))

    assert status == 200
    assert cache == api.CACHE_OK
    assert body["player"] == {
        "nickname": "Alice", "avatar": "https://example.com/a.png", "country": "kz",
        "flag": "🇰🇿", "level": 10, "elo": 2100,
    }
    assert body["matches_requested"] == 10
    assert body["matches_analyzed"] == 2
    assert 0 <= body["score"] <= 100
    assert body["tier"] in "SABCD"
    assert body["tier_name"]
    assert set(body["components"]) == {"combat", "multi", "entry", "clutch"}
    assert set(body["stats"]) == {"adr", "kd", "kr", "mvp", "entry", "clutch", "multi"}
    assert body["averages"]["adr"] == 80.0 and set(body["averages"]) == set(body["stats"])
    # Oldest match first, pretty map names.
    assert [m["map"] for m in body["matches"]] == ["Mirage", "Inferno"]
    assert {m["map"] for m in body["maps"]} == {"Mirage", "Inferno"}
    assert body["maps"][0]["score"] >= body["maps"][1]["score"]
    # Everything must be serialisable.
    json.dumps(body)


def test_profile_link_and_default_match_count():
    client = faceit()
    status, body, _ = api.rating_response(client, query(player="https://www.faceit.com/en/players/Alice"))

    assert status == 200
    assert body["matches_requested"] == api.DEFAULT_MATCHES
    assert client.calls[0] == ("/players", {"nickname": "Alice"})


@pytest.mark.parametrize("params", [
    {},
    {"player": ""},
    {"player": "two words"},
    {"player": "<script>"},
])
def test_bad_nickname(params):
    status, body, cache = api.rating_response(faceit(), query(**params))
    assert (status, cache) == (400, api.NO_CACHE)
    assert body == {"error": api.BAD_NICKNAME}


@pytest.mark.parametrize("matches", ["7", "abc", "-30", "1000"])
def test_bad_match_count(matches):
    status, body, _ = api.rating_response(faceit(), query(player="alice", matches=matches))
    assert status == 400
    assert body == {"error": api.BAD_MATCHES}


def test_unknown_player():
    status, body, cache = api.rating_response(faceit(), query(player="nobody"))
    assert (status, cache) == (404, api.CACHE_NOT_FOUND)
    assert "not found" in body["error"]


def test_player_without_matches():
    status, body, _ = api.rating_response(faceit(history=[]), query(player="alice"))
    assert status == 404
    assert "no CS2 matches" in body["error"]


def test_faceit_down():
    client = faceit()
    client.responses["/players"] = FaceitError("timeout")

    status, body, cache = api.rating_response(client, query(player="alice"))

    assert (status, cache) == (503, api.NO_CACHE)
    assert body == {"error": api.FACEIT_DOWN}


def test_client_is_created_once_from_env(monkeypatch):
    monkeypatch.setattr(api, "_client", None)
    monkeypatch.delenv("FACEIT_API_KEY", raising=False)
    assert api.get_client() is None

    monkeypatch.setenv("FACEIT_API_KEY", "key")
    client = api.get_client()
    assert client is not None
    assert api.get_client() is client


@pytest.fixture
def server(monkeypatch):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), api.RatingHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def get(url):
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, dict(response.headers), json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), json.loads(error.read())


def test_http_handler(server, monkeypatch):
    monkeypatch.setattr(api, "get_client", faceit)

    status, headers, body = get(f"{server}/api/rating?player=alice&matches=30")

    assert status == 200
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert headers["Cache-Control"] == api.CACHE_OK
    assert body["player"]["nickname"] == "Alice"

    status, _, body = get(f"{server}/api/rating?player=nobody")
    assert status == 404


def test_http_handler_without_api_key(server, monkeypatch):
    monkeypatch.setattr(api, "get_client", lambda: None)

    status, headers, body = get(f"{server}/api/rating?player=alice")

    assert status == 500
    assert headers["Cache-Control"] == api.NO_CACHE
    assert body == {"error": api.NOT_CONFIGURED}
