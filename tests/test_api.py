"""End-to-end API behavior, including the page the form lives on."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import wedding_payload


def test_health_names_the_four_engines(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["llm_configured"] is False
    assert body["llm_provider"] is None
    assert "BudgetAllocationEngine" in body["decision_engines"]
    assert "PersonalizedIdeaEngine" in body["decision_engines"]


def test_persona_catalog_marks_the_wedding_flagship(client: TestClient) -> None:
    catalog = client.get("/api/v1/personas").json()
    assert [item["event_type"] for item in catalog] == ["wedding", "birthday", "community"]
    wedding = catalog[0]
    assert wedding["flagship"] is True
    labels = {category["key"]: category["base_percent"] for category in wedding["categories"]}
    assert labels["venue_catering"] == 45.0
    assert labels["contingency"] == 10.0


def test_plan_endpoint_returns_every_section(client: TestClient) -> None:
    response = client.post("/api/v1/plan", json=wedding_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["decision_mode"] == "deterministic"
    assert body["provider"] is None
    assert body["persona_name"] == "Wedding architect"
    assert body["budget"]["lines"]
    assert body["timeline"]["milestones"]
    assert body["checklist"]["items"]
    assert body["ideas"]
    assert body["assumptions"]
    assert sum(line["amount"] for line in body["budget"]["lines"]) == 1_800_000


def test_schedule_mode_changes_with_the_date(client: TestClient) -> None:
    soon = client.post(
        "/api/v1/plan",
        json=wedding_payload(event_date=(date.today() + timedelta(days=10)).isoformat(), guest_count=80),
    )
    mid = client.post(
        "/api/v1/plan",
        json=wedding_payload(event_date=(date.today() + timedelta(days=40)).isoformat(), event_name="Forty day wedding"),
    )
    assert soon.json()["timeline"]["mode"] == "emergency_sprint"
    assert mid.json()["timeline"]["mode"] == "compressed"
    assert soon.json()["timeline"]["warnings"]


def test_repeated_brief_is_cached(client: TestClient) -> None:
    payload = wedding_payload(event_name="Cached wedding")
    first = client.post("/api/v1/plan", json=payload).json()
    second = client.post("/api/v1/plan", json=payload).json()
    assert first["generated_at"] == second["generated_at"]
    stats = client.get("/health").json()["cache"]
    assert stats["hits"] >= 1
    assert stats["entries"] >= 1


def test_rebalance_endpoint_and_a_mismatched_allocation(client: TestClient) -> None:
    plan = client.post("/api/v1/plan", json=wedding_payload()).json()
    allocations = {line["key"]: line["amount"] for line in plan["budget"]["lines"]}
    decor = allocations["decor"]
    response = client.post(
        "/api/v1/rebalance-budget",
        json={
            "event_type": "wedding",
            "total_budget": 1_800_000,
            "guest_count": 250,
            "location_tier": "metro",
            "allocations": allocations,
            "changed_category": "decor",
            "new_amount": decor + 50_000,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert sum(line["amount"] for line in body["lines"]) == 1_800_000
    mismatch = client.post(
        "/api/v1/rebalance-budget",
        json={
            "event_type": "community",
            "total_budget": 1_800_000,
            "guest_count": 250,
            "location_tier": "metro",
            "allocations": allocations,
            "changed_category": "decor",
            "new_amount": decor,
        },
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "invalid_plan_input"


def test_homepage_has_accessible_landmarks(client: TestClient) -> None:
    html = client.get("/").text
    assert "Skip to planner" in html
    assert 'id="main-planner"' in html
    assert 'role="radiogroup"' in html
    assert 'role="tablist"' in html
    assert 'aria-live="polite"' in html
    assert "<label" in html
    assert "EventCraft AI" in html
