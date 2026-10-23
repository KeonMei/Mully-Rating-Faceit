import pytest
import requests

from mully_rating.faceit.client import BASE_URL, TIMEOUT, FaceitClient, FaceitError, to_float, to_int


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self.body = body

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


def client_returning(monkeypatch, result):
    client = FaceitClient("secret-key")
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((url, params, timeout))
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(client.session, "get", fake_get)
    return client, calls


def test_sends_api_key():
    assert FaceitClient("secret-key").session.headers["Authorization"] == "Bearer secret-key"


def test_ok(monkeypatch):
    client, calls = client_returning(monkeypatch, FakeResponse(200, {"player_id": "p"}))
    assert client.get("/players", {"nickname": "a"}) == {"player_id": "p"}
    assert calls == [(BASE_URL + "/players", {"nickname": "a"}, TIMEOUT)]


def test_not_found_is_none(monkeypatch):
    client, _ = client_returning(monkeypatch, FakeResponse(404))
    assert client.get("/players") is None


@pytest.mark.parametrize("result", [
    FakeResponse(401),
    FakeResponse(200, ValueError("not json")),
    requests.ConnectionError("no internet"),
    requests.Timeout("too slow"),
])
def test_errors_become_faceit_error(monkeypatch, result):
    client, _ = client_returning(monkeypatch, result)
    with pytest.raises(FaceitError):
        client.get("/players")


def test_number_helpers():
    assert to_float("1.5") == 1.5
    assert to_float("") == 0
    assert to_float(None) == 0
    assert to_int("3") == 3
    assert to_int("2.0") == 2
    assert to_int("abc") == 0
