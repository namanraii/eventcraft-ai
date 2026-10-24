"""Problem-statement alignment: budgets, timelines, vendors, and ideas."""

from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta

import httpx

from src.core.config import Settings
from src.domain.personas import PERSONAS
from src.domain.schemas import (
    BudgetPlan,
    ChecklistPlan,
    EventRequest,
    EventVertical,
    TimelinePlan,
)
from src.services.budget_engine import BudgetAllocationEngine, split_amount
from src.services.checklist_engine import VendorChecklistManager
from src.services.idea_engine import PersonalizedIdeaEngine
from src.services.llm_orchestrator import EnrichmentResult, LlmOrchestrator
from src.services.planner import build_complete_plan
from src.services.timeline_engine import TimelineMilestoneGenerator
from tests.conftest import wedding_payload


def _request(**overrides: object) -> EventRequest:
    return EventRequest.model_validate(wedding_payload(**overrides))


def test_persona_baselines_sum_to_one() -> None:
    keys = []
    for persona in PERSONAS.values():
        assert abs(sum(category.base_weight for category in persona.categories) - 1) < 1e-9
        assert persona.contingency_key == "contingency"
        keys.append(tuple(category.key for category in persona.categories))
    assert len(set(keys)) == 3


def test_split_amount_is_exact() -> None:
    amounts = split_amount(100, {"a": 1, "b": 1, "c": 1})
    assert sum(amounts.values()) == 100
    assert sorted(amounts.values()) == [33, 33, 34]


def test_default_wedding_protects_food_and_buffer() -> None:
    plan = BudgetAllocationEngine().allocate(_request())
    assert sum(line.amount for line in plan.lines) == 1_800_000
    assert abs(sum(line.percent for line in plan.lines) - 100) < 0.05
    by_key = {line.key: line for line in plan.lines}
    assert 44 <= by_key["venue_catering"].percent <= 46
    assert by_key["contingency"].amount == 180_000
    assert plan.per_guest_total == 7_200


def test_high_food_priority_moves_the_venue_line() -> None:
    plan = BudgetAllocationEngine().allocate(_request(priorities={"venue_catering": 5}))
    venue = next(line for line in plan.lines if line.key == "venue_catering")
    assert venue.percent > 50
    assert sum(line.amount for line in plan.lines) == 1_800_000


def test_destination_wedding_shifts_hospitality() -> None:
    metro = BudgetAllocationEngine().allocate(_request(location_tier="metro", setting="indoor"))
    destination = BudgetAllocationEngine().allocate(
        _request(location_tier="destination", setting="indoor")
    )
    metro_hospitality = next(line for line in metro.lines if line.key == "attire_hospitality")
    away_hospitality = next(line for line in destination.lines if line.key == "attire_hospitality")
    assert away_hospitality.amount > metro_hospitality.amount
    assert any("Destination" in note for note in destination.decision_notes)


def test_birthday_age_changes_the_split() -> None:
    general = BudgetAllocationEngine().allocate(
        _request(event_type="birthday", age_group="general", priorities={})
    )
    kids = BudgetAllocationEngine().allocate(
        _request(event_type="birthday", age_group="kids", priorities={})
    )
    general_show = next(line for line in general.lines if line.key == "entertainment")
    kids_show = next(line for line in kids.lines if line.key == "entertainment")
    assert kids_show.amount > general_show.amount


def test_tiny_metro_wedding_warns_on_the_plate_cost() -> None:
    plan = BudgetAllocationEngine().allocate(
        _request(total_budget=50_000, guest_count=50, location_tier="metro")
    )
    assert plan.warnings
    assert "per guest" in plan.warnings[0]


def test_boundary_budgets_and_guest_counts() -> None:
    engine = BudgetAllocationEngine()
    small = engine.allocate(_request(total_budget=1_000, guest_count=5))
    large = engine.allocate(_request(total_budget=100_000_000, guest_count=50_000))
    assert sum(line.amount for line in small.lines) == 1_000
    assert sum(line.amount for line in large.lines) == 100_000_000


def test_rebalance_keeps_the_total_and_the_buffer_floor() -> None:
    engine = BudgetAllocationEngine()
    original = engine.allocate(_request())
    allocations = {line.key: line.amount for line in original.lines}
    from src.domain.schemas import LocationTier, RebalanceRequest

    moved = engine.rebalance(
        RebalanceRequest(
            event_type=EventVertical.WEDDING,
            total_budget=1_800_000,
            guest_count=250,
            location_tier=LocationTier.METRO,
            allocations=allocations,
            changed_category="decor",
            new_amount=allocations["decor"] + 100_000,
        )
    )
    assert sum(line.amount for line in moved.lines) == 1_800_000
    buffer = next(line for line in moved.lines if line.key == "contingency")
    assert buffer.amount >= int(round(1_800_000 * 0.08))
    decor = next(line for line in moved.lines if line.key == "decor")
    assert decor.amount == allocations["decor"] + 100_000


def test_rebalance_caps_a_category_that_would_erase_the_buffer() -> None:
    engine = BudgetAllocationEngine()
    original = engine.allocate(_request())
    from src.domain.schemas import LocationTier, RebalanceRequest

    moved = engine.rebalance(
        RebalanceRequest(
            event_type=EventVertical.WEDDING,
            total_budget=1_800_000,
            guest_count=250,
            location_tier=LocationTier.METRO,
            allocations={line.key: line.amount for line in original.lines},
            changed_category="venue_catering",
            new_amount=1_800_000,
        )
    )
    assert sum(line.amount for line in moved.lines) == 1_800_000
    assert moved.warnings
    buffer = next(line for line in moved.lines if line.key == "contingency")
    assert buffer.amount >= int(round(1_800_000 * 0.08))


def test_timeline_modes_follow_the_days_remaining() -> None:
    generator = TimelineMilestoneGenerator()
    today = date(2026, 10, 22)
    phased = generator.build(_request(event_date=today + timedelta(days=200)), today=today)
    compressed = generator.build(_request(event_date=today + timedelta(days=40)), today=today)
    sprint = generator.build(_request(event_date=today + timedelta(days=10)), today=today)
    assert phased.mode == "phased"
    assert compressed.mode == "compressed"
    assert sprint.mode == "emergency_sprint"
    assert sprint.milestones
    assert all(today <= item.due_date <= today + timedelta(days=10) for item in sprint.milestones)
    assert any(item.status == "overdue" for item in phased.milestones)


def test_community_checklist_includes_permission_and_mehendi_is_conditional() -> None:
    community = VendorChecklistManager().build(
        _request(
            event_type="community",
            event_name="Ward mela",
            cultural_preferences="Folk music in the park",
            event_date=date.today() + timedelta(days=50),
        )
    )
    roles = [item.vendor_role for item in community.items]
    assert any("permit" in role.lower() or "NOC" in role for role in roles)
    plain = VendorChecklistManager().build(_request(cultural_preferences="A short ceremony at "
        "home"))
    assert all("Mehendi" not in item.vendor_role for item in plain.items)
    with_mehendi = VendorChecklistManager().build(
        _request(cultural_preferences="Mehendi in the morning and a short sangeet")
    )
    names = [item.vendor_role for item in with_mehendi.items]
    assert "Mehendi artist" in names
    assert "Sangeet production" in names


def test_overdue_vendor_lead_time_is_called_out() -> None:
    checklist = VendorChecklistManager().build(
        _request(event_date=date.today() + timedelta(days=20)),
        today=date.today(),
    )
    venue = next(item for item in checklist.items if item.vendor_role == "Venue")
    assert venue.status_hint.startswith("Lead time")
    assert venue.priority == "critical"


def test_ideas_name_the_city_without_a_model() -> None:
    request = _request(city="Jaipur", event_type="wedding")
    budget = BudgetAllocationEngine().allocate(request)
    timeline = TimelineMilestoneGenerator().build(request)
    ideas, tips, note, assumptions = PersonalizedIdeaEngine().compose(request, budget, timeline)
    assert len(ideas) == 3
    assert ideas[0].source == "rules"
    assert any("Jaipur" in idea.why_it_fits or "Jaipur" in idea.summary for idea in ideas)
    assert tips
    assert "INR" in assumptions[0]
    assert "Jaipur" in note


def test_model_failure_still_returns_a_full_plan() -> None:
    class Exploding:
        async def enrich(
            self,
            request: EventRequest,
            budget: BudgetPlan,
            timeline: TimelinePlan,
            checklist: ChecklistPlan,
        ) -> EnrichmentResult | None:
            raise RuntimeError("provider down")

    plan = asyncio.run(build_complete_plan(_request(), Exploding()))
    assert plan.decision_mode == "deterministic"
    assert plan.budget.lines
    assert plan.timeline.milestones
    assert plan.checklist.items
    assert plan.ideas


def test_model_ideas_do_not_replace_the_budget() -> None:
    enrichment = {
        "planner_note": "Keep the courtyard and the separate Jain line.",
        "ideas": [
            {
                "title": "Courtyard supper",
                "summary": "One courtyard and one meal.",
                "why_it_fits": "Jaipur suits an open rite.",
                "signature_experience": "Shehnai at the gate.",
                "sustainability_tip": "Rent the mandap frame.",
                "palette": ["sand", "ivory", "marigold"],
            },
            {
                "title": "Separate Jain counter",
                "summary": "Own ladles and own staff.",
                "why_it_fits": "The brief asks for Jain food.",
                "signature_experience": "A labeled counter elders can trust.",
                "sustainability_tip": "Cook to the RSVP count.",
                "palette": ["leaf", "brass", "white"],
            },
        ],
        "extra_contract_clauses": [
            {"vendor_role": "Caterer", "clause": "The Jain line uses separate pans and ladles."}
        ],
        "sustainability_tips": ["Skip foam flowers."],
    }

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        if request.url.host == "api.groq.com":
            return httpx.Response(500, json={"error": "down"})
        body = json.loads(request.content.decode())
        assert "<untrusted_user_notes>" in body["messages"][1]["content"]
        assert "INR" in body["messages"][1]["content"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(enrichment)}}]},
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        settings = Settings(xai_api_key="test-key", groq_api_key="groq-key", gemini_api_key="")
        async with httpx.AsyncClient(transport=transport) as http:
            orchestrator = LlmOrchestrator(settings, http)
            brief = _request(dietary_notes="Vegetarian with a Jain line")
            before = BudgetAllocationEngine().allocate(brief)
            plan = await build_complete_plan(brief, orchestrator)
            after_amounts = {line.key: line.amount for line in plan.budget.lines}
            before_amounts = {line.key: line.amount for line in before.lines}
            assert after_amounts == before_amounts
            assert seen == ["api.groq.com", "api.x.ai"]
            assert plan.decision_mode == "hybrid"
            assert plan.provider == "spacexai"
            assert plan.ideas[0].source == "model"
            caterer = next(item for item in plan.checklist.items if item.vendor_role == "Caterer")
            assert any("separate pans" in clause for clause in caterer.contract_clauses)

    asyncio.run(run())
