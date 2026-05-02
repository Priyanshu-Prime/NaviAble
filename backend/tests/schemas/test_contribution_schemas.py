"""Unit tests for Pydantic schemas."""
import pytest
from pydantic import ValidationError
from app.schemas.contribution import ContributionCreate


def test_valid_contribution():
    c = ContributionCreate(review="good ramp", latitude=12.97, longitude=77.59, rating=3)
    assert c.review == "good ramp"


def test_latitude_bounds():
    ContributionCreate(review="r", latitude=90, longitude=0, rating=1)
    ContributionCreate(review="r", latitude=-90, longitude=0, rating=1)
    with pytest.raises(ValidationError):
        ContributionCreate(review="r", latitude=90.001, longitude=0, rating=1)
    with pytest.raises(ValidationError):
        ContributionCreate(review="r", latitude=-90.001, longitude=0, rating=1)


def test_rating_bounds():
    ContributionCreate(review="r", latitude=0, longitude=0, rating=1)
    ContributionCreate(review="r", latitude=0, longitude=0, rating=5)
    with pytest.raises(ValidationError):
        ContributionCreate(review="r", latitude=0, longitude=0, rating=0)
    with pytest.raises(ValidationError):
        ContributionCreate(review="r", latitude=0, longitude=0, rating=6)


def test_empty_review_rejected():
    with pytest.raises(ValidationError):
        ContributionCreate(review="", latitude=0, longitude=0, rating=3)


def test_whitespace_review_rejected():
    with pytest.raises(ValidationError):
        ContributionCreate(review="   ", latitude=0, longitude=0, rating=3)


def test_longitude_bounds():
    ContributionCreate(review="r", latitude=0, longitude=180, rating=1)
    ContributionCreate(review="r", latitude=0, longitude=-180, rating=1)
    with pytest.raises(ValidationError):
        ContributionCreate(review="r", latitude=0, longitude=180.001, rating=1)
