"""Dependency injection helpers."""
from fastapi import Request

from app.services.google_places import GooglePlacesService


def get_google_places(request: Request) -> GooglePlacesService:
    return request.app.state.google_places
