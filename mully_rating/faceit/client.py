"""HTTP client for the FACEIT Data API."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://open.faceit.com/data/v4"

# Seconds to wait for FACEIT before giving up on a request.
TIMEOUT = 10


class FaceitError(Exception):
    """FACEIT API is unreachable or answered with an unexpected error."""


class FaceitClient:
    """Small wrapper around the FACEIT Data API.

    One shared session keeps TCP/TLS connections open between requests
    (much faster than a new connection per request) and retries
    rate-limit (429) and server errors with a growing delay.
    """

    def __init__(self, api_key, max_connections=20):

        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )

        adapter = HTTPAdapter(pool_maxsize=max_connections, max_retries=retry)

        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"
        self.session.mount("https://", adapter)

    def get(self, path, params=None):
        """GET a FACEIT endpoint. Returns the JSON body, or None for 404."""

        try:
            response = self.session.get(BASE_URL + path, params=params, timeout=TIMEOUT)
        except requests.RequestException as error:
            raise FaceitError(f"FACEIT request failed: {path}") from error

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise FaceitError(f"FACEIT returned HTTP {response.status_code} for {path}")

        try:
            return response.json()
        except ValueError as error:
            raise FaceitError(f"FACEIT returned invalid JSON for {path}") from error


def to_float(value, default=0.0):
    """FACEIT sends numbers as strings; turn them into floats safely."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    return int(to_float(value, default))
