"""Every challenge deliverable, for every vertical, from one plan response."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import wedding_payload


def _assert_plan(plan: dict[str, object], city: str) -> None:
    budget = plan["budget"]
    assert isinstance(budget, dict)
    lines = budget["lines"]
    assert isinstance(lines, list) and lines
    amounts = [line["amount"] for line in lines]
    assert sum(amounts) == budget["total_budget"]
    assert round(sum(line["percent"] for line in lines), 1) == 100.0
    assert budget["decision_notes"]
    timeline = plan["timeline"]
    assert isinstance(timeline, dict)
    assert timeline["milestones"]
    assert timeline["mode"] in {"emergency_sprint", "compressed", "phased"}
    checklist = plan["checklist"]
    assert isinstance(checklist, dict) and checklist["items"]
    ideas = plan["ideas"]
    assert isinstance(ideas, list) and ideas
    blob = " ".join(idea["title"] + idea["summary"] for idea in ideas)
    assert city in blob or city in str(plan["planner_note"])


def test_wedding_birthday_and_community_each_return_a_full_plan(client: TestClient) -> None:
    soon = (date.today() + timedelta(days=40)).isoformat()
    wedding = client.post("/api/v1/plan", json=wedding_payload())
    birthday = client.post(
        "/api/v1/plan",
        json=wedding_payload(
            event_type="birthday",
            event_name="Ananya turns 30",
            host_names="Ananya",
            total_budget=150_000,
            guest_count=40,
            event_date=soon,
            location_tier="metro",
            city="Bengaluru",
            age_group="milestone_30",
            setting="indoor",
        ),
    )
    community = client.post(
        "/api/v1/plan",
        json=wedding_payload(
            event_type="community",
            event_name="Pune neighbourhood mela",
            host_names="Residents association",
            total_budget=800_000,
            guest_count=2000,
            event_date=soon,
            location_tier="city",
            city="Pune",
            setting="outdoor",
            cultural_preferences="Permit not filed",
        ),
    )
    assert wedding.status_code == birthday.status_code == community.status_code == 200
    wedding_plan = wedding.json()
    birthday_plan = birthday.json()
    community_plan = community.json()
    _assert_plan(wedding_plan, "Jaipur")
    _assert_plan(birthday_plan, "Bengaluru")
    _assert_plan(community_plan, "Pune")

    assert wedding_plan["budget"]["contingency_amount"] == 180_000
    cake = [line for line in birthday_plan["budget"]["lines"] if line["key"] == "cake_dessert"]
    assert cake and cake[0]["amount"] > 0
    roles = [item["vendor_role"] for item in community_plan["checklist"]["items"]]
    assert any("permit" in role.lower() or "NOC" in role for role in roles)
    assert wedding_plan["decision_mode"] == "deterministic"
