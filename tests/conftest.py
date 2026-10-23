import pytest

from mully_rating.faceit.matches import clear_cache


@pytest.fixture(autouse=True)
def empty_match_cache():
    clear_cache()
    yield
    clear_cache()
