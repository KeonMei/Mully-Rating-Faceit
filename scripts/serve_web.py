"""Run the website on your computer, without Vercel.

    python scripts/serve_web.py            -> http://localhost:8000
    python scripts/serve_web.py --port 3000

Serves the pages from public/ and the same /api/rating code that runs on
Vercel. Needs FACEIT_API_KEY in .env (the Telegram token is not needed).
"""

import argparse
import functools
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

# Make "mully_rating" importable when the script is run from anywhere.
sys.path.insert(0, str(ROOT))

from mully_rating.web.api import RatingHandler  # noqa: E402


class DevHandler(RatingHandler, SimpleHTTPRequestHandler):
    """/api/rating goes to the API, everything else is a file from public/."""

    def do_GET(self):
        if self.path == "/api/rating" or self.path.startswith("/api/rating?"):
            RatingHandler.do_GET(self)
        else:
            SimpleHTTPRequestHandler.do_GET(self)


def make_server(port=8000, host="127.0.0.1"):
    handler = functools.partial(DevHandler, directory=str(PUBLIC))
    return ThreadingHTTPServer((host, port), handler)


def main():

    parser = argparse.ArgumentParser(description="Run the Mully Rating website locally.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass  # without python-dotenv, FACEIT_API_KEY must be set in the shell

    server = make_server(args.port)
    print(f"Mully Rating website: http://localhost:{server.server_address[1]}  (Ctrl+C to stop)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
