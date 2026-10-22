"""Shared fixtures. The app under test has no model keys and a fresh cache."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from main import create_app
from src.core.config import Settings


def wedding_payload(**overrides: object) -> dict[str, object]:
    """A valid wedding brief. Override any field, including ones you want removed."""
    payload: dict[str, object] = {
        "event_type": "wedding",
        "event_name": "Meera and Arjun",
        "host_names": "Meera and Arjun",
        "total_budget": 1_800_000,
        "guest_count": 250,
        "event_date": (date.today() + timedelta(days=240)).isoformat(),
        "location_tier": "metro",
        "city": "Jaipur",
        "vibe": "Courtyard ceremony",
        "cultural_preferences": "A short Hindu ceremony",
        "dietary_notes": "Vegetarian",
        "custom_notes": "Keep the guest list kind to elders",
        "setting": "indoor",
        "priorities": {},
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client() -> TestClient:
    """Return a client whose lifespan, cache, and limiter are isolated."""
    settings = Settings(
        xai_api_key="",
        groq_api_key="",
        gemini_api_key="",
        rate_limit_per_minute=60,
    )
    application = create_app(settings)
    with TestClient(application) as test_client:
        yield test_client
