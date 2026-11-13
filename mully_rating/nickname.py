"""Reading a FACEIT nickname from what the user typed."""

import re

# FACEIT nicknames use latin letters, digits, "-" and "_".
NICKNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{2,32}$")

# https://www.faceit.com/en/players/s1mple -> s1mple
PROFILE_URL_RE = re.compile(
    r"faceit\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?players/([^/?#\s]+)",
    re.IGNORECASE
)


def is_nickname(text):
    return bool(NICKNAME_RE.match(text or ""))


def extract_nickname(text):
    """Nickname from a message: plain nickname or FACEIT profile link."""

    text = (text or "").strip()

    url_match = PROFILE_URL_RE.search(text)

    if url_match:
        text = url_match.group(1)

    text = text.lstrip("@")

    return text if is_nickname(text) else None
