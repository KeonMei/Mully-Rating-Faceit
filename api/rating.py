"""Vercel Python function: GET /api/rating?player=<nickname>&matches=30

Vercel turns every file in api/ that defines a `handler` class into an
endpoint. The real code is in mully_rating/web/api.py, so the local dev
server (scripts/serve_web.py) and the tests use the same logic.
"""

import sys
from pathlib import Path

# Make the mully_rating package (project root) importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mully_rating.web.api import RatingHandler as handler  # noqa: E402

__all__ = ["handler"]
