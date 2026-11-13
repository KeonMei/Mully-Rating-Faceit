"""Checks of the files Vercel reads, so a broken deploy shows up in tests."""

import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_vercel_function_exposes_handler():
    spec = importlib.util.spec_from_file_location("vercel_rating", ROOT / "api" / "rating.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert issubclass(module.handler, BaseHTTPRequestHandler)


def test_vercel_json():
    config = json.loads((ROOT / "vercel.json").read_text())

    assert config["framework"] is None  # "Other": static files from public/
    assert "api/*.py" in config["functions"]
    assert (ROOT / "public" / "index.html").exists()


def pinned(lines, package):
    for line in lines:
        match = re.fullmatch(rf"{package}==([\w.]+)", line.strip())
        if match:
            return match.group(1)
    return None


def test_website_and_bot_pin_the_same_requests():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    requirements = (ROOT / "requirements.txt").read_text().splitlines()

    assert pinned(project["dependencies"], "requests") == pinned(requirements, "requests")


def test_website_needs_no_bot_dependencies():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    names = {re.split(r"[=<>!~ ]", dep)[0] for dep in project["dependencies"]}

    assert names == {"requests"}


def test_function_does_not_import_bot_libraries():
    # Vercel installs only `requests`; importing telegram, matplotlib or
    # dotenv in the API would crash the deployed function.
    code = (
        "import importlib.util, sys; "
        f"spec = importlib.util.spec_from_file_location('rating', {str(ROOT / 'api' / 'rating.py')!r}); "
        "module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
        "print(sorted({name.split('.')[0] for name in sys.modules} & {'telegram', 'matplotlib', 'dotenv'}))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)

    assert result.stdout.strip() == "[]"
