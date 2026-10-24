"""Cache behavior, response compression, and a bound on local planning time."""

from __future__ import annotations

import time
from datetime import date, timedelta

from fastapi.testclient import TestClient

from src.core.cache import ResponseCache, plan_cache_key
from src.domain.schemas import EventRequest, EventVertical, LocationTier, Setting
from src.services.budget_engine import BudgetAllocationEngine
from src.services.checklist_engine import VendorChecklistManager
from src.services.idea_engine import PersonalizedIdeaEngine
from src.services.timeline_engine import TimelineMilestoneGenerator
from tests.conftest import wedding_payload


def test_cache_key_ignores_dict_order() -> None:
    first = plan_cache_key({"b": 1, "a": {"d": 2, "c": 3}})
    second = plan_cache_key({"a": {"c": 3, "d": 2}, "b": 1})
    assert first == second
    assert first != plan_cache_key({"a": {"c": 4, "d": 2}, "b": 1})


def test_ttl_expiry(monkeypatch) -> None:
    clock = {"now": 1_000.0}
    monkeypatch.setattr("src.core.cache.time.monotonic", lambda: clock["now"])
    cache = ResponseCache(max_entries=4, ttl_seconds=10)
    cache.set("plan", {"ok": True})
    assert cache.get("plan") == {"ok": True}
    clock["now"] = 1_011.0
    assert cache.get("plan") is None
    assert cache.misses == 1


def test_lru_eviction(monkeypatch) -> None:
    monkeypatch.setattr("src.core.cache.time.monotonic", lambda: 50.0)
    cache = ResponseCache(max_entries=2, ttl_seconds=100)
    cache.set("a", {"n": 1})
    cache.set("b", {"n": 2})
    assert cache.get("a") == {"n": 1}
    cache.set("c", {"n": 3})
    assert cache.get("b") is None
    assert cache.get("a") == {"n": 1}
    assert cache.get("c") == {"n": 3}


def test_one_hundred_local_plans_stay_under_half_a_second() -> None:
    request = EventRequest(
        event_type=EventVertical.WEDDING,
        event_name="Meera and Arjun",
        host_names="Meera and Arjun",
        total_budget=1_800_000,
        guest_count=250,
        event_date=date.today() + timedelta(days=240),
        location_tier=LocationTier.DESTINATION,
        city="Jaipur",
        setting=Setting.OUTDOOR,
    )
    started = time.perf_counter()
    for _ in range(100):
        budget = BudgetAllocationEngine().allocate(request)
        timeline = TimelineMilestoneGenerator().build(request, today=date.today())
        VendorChecklistManager().build(request, today=date.today())
        PersonalizedIdeaEngine().compose(request, budget, timeline)
    elapsed = time.perf_counter() - started
    assert elapsed < 0.5


def test_plan_response_is_gzipped(client: TestClient) -> None:
    response = client.post(
        "/api/v1/plan",
        json=wedding_payload(),
        headers={"Accept-Encoding": "gzip"},
    )
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"
    body = response.json()
    assert body["budget"]["total_budget"] == 1_800_000
