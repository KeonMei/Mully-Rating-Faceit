import importlib.util
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from mully_rating.web import api

from fakes import FakeClient, history_item, match_round, player_stats

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "serve_web.py"

spec = importlib.util.spec_from_file_location("serve_web", SCRIPT)
serve_web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serve_web)


@pytest.fixture
def base_url(monkeypatch):
    client = FakeClient({
        "/players": {"player_id": "pid", "nickname": "Alice", "games": {"cs2": {}}},
        "/players/pid/games/cs2/stats": {"items": [history_item("m1")]},
        "/matches/m1/stats": {"rounds": [match_round({"pid": player_stats()})]},
    })
    monkeypatch.setattr(api, "get_client", lambda: client)

    server = serve_web.make_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def read(url):
    with urllib.request.urlopen(url) as response:
        return response.status, response.headers.get_content_type(), response.read()


def test_serves_pages_from_public(base_url):
    status, content_type, body = read(f"{base_url}/")
    assert (status, content_type) == (200, "text/html")
    assert b"Mully Rating" in body

    for path, expected in [("/app.js", "javascript"), ("/style.css", "text/css"), ("/favicon.svg", "image/svg+xml")]:
        status, content_type, _ = read(base_url + path)
        assert status == 200
        assert expected in content_type


def test_serves_the_api(base_url):
    status, content_type, body = read(f"{base_url}/api/rating?player=alice&matches=10")
    assert (status, content_type) == (200, "application/json")
    assert json.loads(body)["player"]["nickname"] == "Alice"


def test_files_outside_public_are_not_served(base_url):
    with pytest.raises(urllib.error.HTTPError) as error:
        read(f"{base_url}/../.env.example")
    assert error.value.code == 404
