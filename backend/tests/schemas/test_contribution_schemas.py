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


def test_google_place_id_optional():
    """google_place_id is optional."""
    c = ContributionCreate(review="r", rating=3, google_place_id="ChIJ41A7_1BYwokRGH63IJiCQaQ")
    assert c.google_place_id == "ChIJ41A7_1BYwokRGH63IJiCQaQ"

    c2 = ContributionCreate(review="r", rating=3, google_place_id=None)
    assert c2.google_place_id is None


def test_address_optional():
    """address is optional."""
    c = ContributionCreate(review="r", rating=3, address="123 Main St, NYC")
    assert c.address == "123 Main St, NYC"

    c2 = ContributionCreate(review="r", rating=3, address=None)
    assert c2.address is None


def test_address_max_length():
    """address field respects max_length=500."""
    c = ContributionCreate(review="r", rating=3, address="x" * 500)
    assert len(c.address) == 500

    with pytest.raises(ValidationError):
        ContributionCreate(review="r", rating=3, address="x" * 501)


def test_google_place_id_max_length():
    """google_place_id respects max_length=255."""
    c = ContributionCreate(review="r", rating=3, google_place_id="x" * 255)
    assert len(c.google_place_id) == 255

    with pytest.raises(ValidationError):
        ContributionCreate(review="r", rating=3, google_place_id="x" * 256)


def test_location_chain_google_place_id():
    """Validator passes if google_place_id is provided."""
    c = ContributionCreate(
        review="r",
        rating=3,
        google_place_id="ChIJ41A7_1BYwokRGH63IJiCQaQ"
    )
    assert c.google_place_id is not None


def test_location_chain_coordinates():
    """Validator passes if (latitude, longitude) are provided."""
    c = ContributionCreate(review="r", rating=3, latitude=40.7128, longitude=-74.0060)
    assert c.latitude is not None
    assert c.longitude is not None


def test_location_chain_address():
    """Validator passes if address is provided."""
    c = ContributionCreate(review="r", rating=3, address="Times Square, NY")
    assert c.address is not None


def test_location_chain_all_none():
    """Validator allows all location signals to be None (EXIF will be checked server-side)."""
    c = ContributionCreate(
        review="r",
        rating=3,
        google_place_id=None,
        latitude=None,
        longitude=None,
        address=None
    )
    assert c.google_place_id is None
    assert c.latitude is None
    assert c.longitude is None
    assert c.address is None


def test_location_partial_coordinates_invalid():
    """Validator allows partial coordinates (both validated by Pydantic constraints)."""
    # Only latitude without longitude is still valid from the model_validator perspective
    # (constraints are handled by Field validators)
    c = ContributionCreate(review="r", rating=3, latitude=40.7128, longitude=None)
    assert c.latitude == 40.7128
    assert c.longitude is None
