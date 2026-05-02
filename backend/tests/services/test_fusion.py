"""Unit tests for trust score fusion."""
import pytest
from app.core.config import Settings
from app.services.fusion import assign_status, compute_trust_score

# Test settings with valid weights
@pytest.fixture
def s():
    return Settings(database_url="postgresql+psycopg://x:x@localhost/x")


def test_exact_value(s):
    # 0.6 * 0.8 + 0.4 * 0.5 = 0.48 + 0.20 = 0.68
    assert compute_trust_score(0.8, 0.5, settings=s) == 0.68


def test_assign_public(s):
    assert assign_status(0.70) == "PUBLIC"
    assert assign_status(1.0) == "PUBLIC"


def test_assign_caveat(s):
    assert assign_status(0.40) == "CAVEAT"
    assert assign_status(0.69) == "CAVEAT"


def test_assign_hidden(s):
    assert assign_status(0.39) == "HIDDEN"
    assert assign_status(0.0) == "HIDDEN"


def test_out_of_range_raises(s):
    with pytest.raises(ValueError):
        compute_trust_score(-0.1, 0.5, settings=s)
    with pytest.raises(ValueError):
        compute_trust_score(0.5, 1.1, settings=s)


def test_result_in_unit_interval(s):
    for v, n in [(0.0, 0.0), (1.0, 1.0), (0.5, 0.5), (0.3, 0.9)]:
        result = compute_trust_score(v, n, settings=s)
        assert 0.0 <= result <= 1.0
