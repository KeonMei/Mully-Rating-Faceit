import importlib.util
from pathlib import Path

import pytest

from mully_rating.rating.formula import ANCHORS

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "calibrate.py"


def load_script():
    spec = importlib.util.spec_from_file_location("calibrate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


calibrate = load_script()


def test_percentile():
    values = [5, 1, 4, 2, 3]
    assert calibrate.percentile(values, 0) == 1
    assert calibrate.percentile(values, 50) == 3
    assert calibrate.percentile(values, 100) == 5
    assert calibrate.percentile(values, 25) == 2
    assert calibrate.percentile(values, 10) == pytest.approx(1.4)
    assert calibrate.percentile([7], 95) == 7


def test_suggest_anchors_uses_p10_median_p95():
    players = [{name: float(i) for name in ANCHORS} for i in range(1, 102)]  # 1..101

    suggestions = calibrate.suggest_anchors(players)

    assert set(suggestions) == set(ANCHORS)
    assert suggestions["adr"] == (11.0, 51.0, 96.0)


def test_script_prints_players_and_anchors(monkeypatch, capsys):
    from fakes import FakeClient, history_item, match_round, player_stats

    players = {"alice": ("p1", 95), "bob": ("p2", 70)}
    responses = {
        "/players": lambda params: (
            {"player_id": players[params["nickname"]][0], "nickname": params["nickname"].title(),
             "games": {"cs2": {"skill_level": 9}}}
            if params["nickname"] in players else None
        ),
    }
    for nickname, (player_id, adr) in players.items():
        responses[f"/players/{player_id}/games/cs2/stats"] = {"items": [history_item(f"m-{player_id}", adr=adr)]}
        responses[f"/matches/m-{player_id}/stats"] = {"rounds": [match_round({player_id: player_stats(double=3)})]}

    monkeypatch.setattr(calibrate, "FaceitClient", lambda api_key: FakeClient(responses))
    monkeypatch.setattr(calibrate, "load_dotenv", lambda: None)
    monkeypatch.setenv("FACEIT_API_KEY", "key")
    monkeypatch.setattr("sys.argv", ["calibrate.py", "alice", "bob", "nobody"])

    calibrate.main()

    out = capsys.readouterr().out
    assert "Alice" in out and "Bob" in out
    assert "nobody" in out and "skipped" in out
    assert "Suggested ANCHORS from 2 players" in out
    assert '"adr": (72.5, 82.5, 93.75),' in out
