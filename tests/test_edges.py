"""Branches the main flows do not hit: guards, fallbacks, and bad input."""

from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta

import httpx
import pytest
from pydantic import ValidationError

from src.core.config import Settings
from src.core.security import (
    TokenBucketLimiter,
    _content_length,
    sanitize_event_request,
    screen_text,
)
from src.domain.personas import get_persona
from src.domain.schemas import (
    EventRequest,
    EventVertical,
    LocationTier,
    RebalanceRequest,
    VendorClause,
)
from src.services.budget_engine import (
    BudgetAllocationEngine,
    _apply_shift,
    _enforce_floor,
    _largest_other,
    _percents,
    _repair_sum,
    distribute,
    split_amount,
)
from src.services.checklist_engine import VendorChecklistManager
from src.services.idea_engine import _group
from src.services.llm_orchestrator import LlmOrchestrator, _message_text, _parse_enrichment
from src.services.planner import _merge_clauses
from src.services.timeline_engine import TimelineMilestoneGenerator, _dedupe
from tests.conftest import wedding_payload
from tests.test_alignment import _request


def test_provider_order_without_groq() -> None:
    none = Settings(xai_api_key="", groq_api_key="", gemini_api_key="")
    spacex = Settings(xai_api_key="x", groq_api_key="", gemini_api_key="")
    gemini = Settings(xai_api_key="", groq_api_key="", gemini_api_key="g")
    groq = Settings(xai_api_key="", groq_api_key="g", gemini_api_key="")
    assert groq.active_provider_name() == "groq"
    assert none.active_provider_name() is None
    assert spacex.active_provider_name() == "spacexai"
    assert gemini.active_provider_name() == "gemini"


def test_empty_text_and_markup_that_erases_a_name() -> None:
    assert screen_text("", "vibe") == ""
    brief = EventRequest.model_validate(wedding_payload(event_name="<b>A</b>", city="<i>Z</i>"))
    with pytest.raises(Exception, match="event name"):
        sanitize_event_request(brief)
    city = EventRequest.model_validate(wedding_payload(city="<i>Z</i>"))
    with pytest.raises(Exception, match="city"):
        sanitize_event_request(city)


def test_rate_bucket_prunes_and_bad_content_length_is_ignored() -> None:
    limiter = TokenBucketLimiter(1)
    now = 1_000.0
    for index in range(4096):
        limiter._buckets[f"k{index}"] = (1.0, now - 1_000)
    limiter._buckets["fresh"] = (1.0, now)
    limiter._prune(now)
    assert "fresh" in limiter._buckets
    assert "k0" not in limiter._buckets
    assert _content_length([(b"content-length", b"nope")]) is None
    assert _content_length([(b"host", b"local")]) is None


def test_schema_rejects_dates_priorities_and_allocations() -> None:
    yesterday = (date.today() - timedelta(days=30)).isoformat()
    with pytest.raises(ValidationError):
        EventRequest.model_validate(wedding_payload(event_date=yesterday))
    far = (date.today() + timedelta(days=365 * 4)).isoformat()
    with pytest.raises(ValidationError):
        EventRequest.model_validate(wedding_payload(event_date=far))
    with pytest.raises(ValidationError):
        EventRequest.model_validate(wedding_payload(total_budget=True))
    with pytest.raises(ValidationError):
        EventRequest.model_validate(wedding_payload(priorities={"Venue": 3}))
    with pytest.raises(ValidationError):
        EventRequest.model_validate(wedding_payload(priorities={"venue_catering": True}))
    with pytest.raises(ValidationError):
        EventRequest.model_validate(wedding_payload(priorities={f"k{i}": 3 for i in range(13)}))
    with pytest.raises(ValidationError):
        EventRequest.model_validate(wedding_payload(priorities="no"))
    with pytest.raises(ValidationError):
        RebalanceRequest(
            event_type=EventVertical.WEDDING,
            total_budget=1_800_000,
            guest_count=250,
            location_tier=LocationTier.METRO,
            allocations={},
            changed_category="decor",
            new_amount=1,
        )
    with pytest.raises(ValidationError):
        RebalanceRequest(
            event_type=EventVertical.WEDDING,
            total_budget=1_800_000,
            guest_count=250,
            location_tier=LocationTier.METRO,
            allocations={"Bad": 1},
            changed_category="decor",
            new_amount=1,
        )
    with pytest.raises(ValidationError):
        RebalanceRequest(
            event_type=EventVertical.WEDDING,
            total_budget=1_800_000,
            guest_count=250,
            location_tier=LocationTier.METRO,
            allocations={"decor": -1},
            changed_category="decor",
            new_amount=1,
        )


def test_unknown_persona_category_raises() -> None:
    assert get_persona("wedding").category("decor").key == "decor"
    with pytest.raises(KeyError):
        get_persona("wedding").category("not-a-line")


def test_budget_edges() -> None:
    assert split_amount(0, {}) == {}
    assert split_amount(10, {"a": 0, "b": 0}) == {"a": 5, "b": 5}
    with pytest.raises(ValueError):
        split_amount(-1, {"a": 1})
    assert _percents({"a": 0}, 0) == {"a": 0.0}
    repaired = _repair_sum({"a": 0, "b": 5}, 3, "a")
    assert sum(repaired.values()) == 3
    untouched = _enforce_floor({"contingency": 50, "decor": 10}, "contingency", 40, set())
    assert untouched["contingency"] == 50
    drained = _enforce_floor({"contingency": 50, "decor": 10}, "contingency", 80, set())
    assert drained["decor"] == 0
    covered = _enforce_floor({"contingency": 50, "decor": 40}, "contingency", 70, set())
    assert covered["contingency"] == 70
    assert _largest_other({}, "only") == "only"
    assert distribute(0, {}, set(), 0) == {}
    tight = distribute(10, {"a": 5, "b": 5}, set(), 8)
    assert sum(tight.values()) == 10
    notes: list[str] = []
    weights = {"a": 0.5, "b": 0.5}
    _apply_shift(weights, {}, None, notes)
    _apply_shift(weights, {"missing": 0.1}, "nope", notes)
    _apply_shift(weights, {"a": -0.5, "b": 0.5}, "too small", notes)
    assert any("1 percent" in note for note in notes)
    before = dict(weights)
    _apply_shift(weights, {"a": 0.2}, "unbalanced", notes)
    assert weights == before


def test_rebalance_buffer_and_an_unknown_category() -> None:
    engine = BudgetAllocationEngine()
    original = engine.allocate(_request())
    allocations = {line.key: line.amount for line in original.lines}
    low = engine.rebalance(
        RebalanceRequest(
            event_type=EventVertical.WEDDING,
            total_budget=1_800_000,
            guest_count=250,
            location_tier=LocationTier.METRO,
            allocations=allocations,
            changed_category="contingency",
            new_amount=1,
        )
    )
    assert any("buffer" in warning.lower() for warning in low.warnings)
    huge = engine.rebalance(
        RebalanceRequest(
            event_type=EventVertical.WEDDING,
            total_budget=1_800_000,
            guest_count=250,
            location_tier=LocationTier.METRO,
            allocations=allocations,
            changed_category="contingency",
            new_amount=2_000_000,
        )
    )
    assert sum(line.amount for line in huge.lines) == 1_800_000
    same = engine.rebalance(
        RebalanceRequest(
            event_type=EventVertical.WEDDING,
            total_budget=1_800_000,
            guest_count=250,
            location_tier=LocationTier.METRO,
            allocations=allocations,
            changed_category="decor",
            new_amount=allocations["decor"],
        )
    )
    assert any("kept" in note for note in same.decision_notes)
    bad = dict(allocations)
    bad["extra"] = bad.pop("decor")
    with pytest.raises(Exception, match="does not match"):
        engine.rebalance(
            RebalanceRequest(
                event_type=EventVertical.WEDDING,
                total_budget=1_800_000,
                guest_count=250,
                location_tier=LocationTier.METRO,
                allocations=bad,
                changed_category="decor",
                new_amount=1,
            )
        )
    with pytest.raises(Exception, match="not part"):
        engine.rebalance(
            RebalanceRequest(
                event_type=EventVertical.WEDDING,
                total_budget=1_800_000,
                guest_count=250,
                location_tier=LocationTier.METRO,
                allocations=allocations,
                changed_category="not_a_line",
                new_amount=1,
            )
        )
    off = dict(allocations)
    off["decor"] += 1
    with pytest.raises(Exception, match="add up"):
        engine.rebalance(
            RebalanceRequest(
                event_type=EventVertical.WEDDING,
                total_budget=1_800_000,
                guest_count=250,
                location_tier=LocationTier.METRO,
                allocations=off,
                changed_category="decor",
                new_amount=off["decor"],
            )
        )


def test_past_community_date_and_duplicate_milestones() -> None:
    today = date(2026, 10, 22)
    past = TimelineMilestoneGenerator().build(
        _request(event_type="community", event_date=today - timedelta(days=2), guest_count=200),
        today=today,
    )
    assert any("past" in warning.lower() for warning in past.warnings)
    sprint = TimelineMilestoneGenerator().build(
        _request(event_date=today, guest_count=40),
        today=today,
    )
    assert sprint.mode == "emergency_sprint"
    first = sprint.milestones[0]
    assert _dedupe([first, first]) == [first]


def test_small_rupee_grouping_and_blank_clause() -> None:
    assert _group(42) == "42"
    plan = VendorChecklistManager().build(_request())
    blank = VendorClause(vendor_role="  ", clause="x")
    merged = _merge_clauses(plan, [blank])
    assert merged.items


def test_model_text_shapes_and_a_dead_provider() -> None:
    assert _message_text({"content": [{"text": "a"}, "b", {}]}) == "ab"
    assert _message_text({"content": 1}) == ""
    sample = {
        "planner_note": "note",
        "ideas": [
            {
                "title": "One",
                "summary": "Two",
                "why_it_fits": "Three",
                "signature_experience": "Four",
                "sustainability_tip": "Five",
                "palette": ["sand"],
            },
            {
                "title": "Six",
                "summary": "Seven",
                "why_it_fits": "Eight",
                "signature_experience": "Nine",
                "sustainability_tip": "Ten",
                "palette": ["ink"],
            },
        ],
        "extra_contract_clauses": [],
        "sustainability_tips": ["  ", "Skip foam."],
    }
    fenced = "```json\n" + json.dumps(sample) + "\n```"
    assert _parse_enrichment(fenced).ideas
    sample["ideas"] = sample["ideas"][:1]
    with pytest.raises(ValueError):
        _parse_enrichment(json.dumps(sample))

    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        content = "" if calls["n"] == 1 else "not-json"
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    async def run() -> None:
        settings = Settings(xai_api_key="x", groq_api_key="", gemini_api_key="g")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            result = await LlmOrchestrator(settings, http).enrich(
                _request(),
                BudgetAllocationEngine().allocate(_request()),
                TimelineMilestoneGenerator().build(_request()),
                VendorChecklistManager().build(_request()),
            )
        assert result is None

    asyncio.run(run())
