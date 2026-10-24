"""Locks the flagship numbers and the mode boundaries the engines must keep."""

from __future__ import annotations

from datetime import date, timedelta

from src.domain.personas import get_persona
from src.domain.schemas import EventRequest, EventVertical, LocationTier, RebalanceRequest
from src.services.budget_engine import BudgetAllocationEngine
from src.services.idea_engine import PersonalizedIdeaEngine
from src.services.timeline_engine import TimelineMilestoneGenerator
from tests.test_alignment import _request


def _flagship() -> EventRequest:
    today = date.today()
    return EventRequest.model_validate(
        {
            "event_type": "wedding",
            "event_name": "Meera and Arjun",
            "host_names": "Meera Iyer and Arjun Khanna",
            "total_budget": 1_800_000,
            "guest_count": 250,
            "event_date": (today + timedelta(days=240)).isoformat(),
            "location_tier": "destination",
            "city": "Jaipur",
            "setting": "outdoor",
            "vibe": "Modern Rajasthani courtyard wedding",
            "cultural_preferences": "Hindu pheras, mehendi, and a short sangeet.",
            "dietary_notes": "Vegetarian feast with a separate Jain line.",
            "custom_notes": "Keep the baraat short.",
            "priorities": {"venue_catering": 5, "decor": 2},
        }
    )


def test_flagship_wedding_allocation_is_stable() -> None:
    request = _flagship()
    plan = BudgetAllocationEngine().allocate(request)
    amounts = {line.key: (line.amount, line.percent) for line in plan.lines}
    assert amounts == {
        "venue_catering": (1_075_424, 59.7),
        "decor": (91_525, 5.1),
        "photo_video": (164_746, 9.2),
        "attire_hospitality": (178_475, 9.9),
        "entertainment": (109_830, 6.1),
        "contingency": (180_000, 10.0),
    }
    assert sum(line.amount for line in plan.lines) == request.total_budget
    timeline = TimelineMilestoneGenerator().build(request, today=date.today())
    ideas, _, _, _ = PersonalizedIdeaEngine().compose(request, plan, timeline)
    assert [idea.title for idea in ideas] == [
        "Courtyard ceremony, short baraat",
        "Two kitchen lines, one dining hall",
        "Heirloom textile mandap",
    ]


def test_timeline_mode_boundaries_are_exact() -> None:
    today = date.today()
    generator = TimelineMilestoneGenerator()

    def mode(days: int) -> str:
        plan = generator.build(_request(event_date=today + timedelta(days=days)), today=today)
        return plan.mode

    assert mode(13) == "emergency_sprint"
    assert mode(14) == "compressed"
    assert mode(89) == "compressed"
    assert mode(90) == "phased"


def test_category_lookup_returns_the_first_spec() -> None:
    persona = get_persona("wedding")
    for spec in persona.categories:
        assert persona.category(spec.key) is spec


def test_phase_names_follow_first_seen_order() -> None:
    today = date.today()
    plan = TimelineMilestoneGenerator().build(
        _request(event_date=today + timedelta(days=200)),
        today=today,
    )
    seen: list[str] = []
    for milestone in plan.milestones:
        if milestone.phase not in seen:
            seen.append(milestone.phase)
    assert plan.phases == seen


def test_rebalance_keeps_the_sum_and_the_buffer_floor() -> None:
    engine = BudgetAllocationEngine()
    original = engine.allocate(_request())
    allocations = {line.key: line.amount for line in original.lines}
    persona = get_persona(EventVertical.WEDDING)
    floor = int(round(original.total_budget * persona.contingency_floor))
    for key, amount in (("decor", 0), ("decor", 900_000), ("contingency", 1)):
        moved = engine.rebalance(
            RebalanceRequest(
                event_type=EventVertical.WEDDING,
                total_budget=original.total_budget,
                guest_count=original.guest_count,
                location_tier=LocationTier.METRO,
                allocations=allocations,
                changed_category=key,
                new_amount=amount,
            )
        )
        assert sum(line.amount for line in moved.lines) == original.total_budget
        buffer = next(line for line in moved.lines if line.key == "contingency")
        assert buffer.amount >= floor
