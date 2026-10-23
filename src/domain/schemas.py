"""Strict request and response models for the planner API.

Money is an integer number of rupees. Percents are derived from those
integers so a plan always sums back to the budget the person entered.
The model is never asked to do this arithmetic.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PRIORITY_KEY = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


class EventVertical(str, Enum):
    """The three celebration verticals in the challenge brief."""

    WEDDING = "wedding"
    BIRTHDAY = "birthday"
    COMMUNITY = "community"


class LocationTier(str, Enum):
    """Cost context for viability warnings. It does not inflate the budget."""

    METRO = "metro"
    CITY = "city"
    DESTINATION = "destination"


class AgeGroup(str, Enum):
    """Birthday age band. Ignored for the other verticals."""

    KIDS = "kids"
    TEENS = "teens"
    MILESTONE_21 = "milestone_21"
    MILESTONE_30 = "milestone_30"
    MILESTONE_50 = "milestone_50"
    GENERAL = "general"


class Setting(str, Enum):
    """Where the event happens. Outdoor plans shift weight toward safety."""

    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    MIXED = "mixed"


class EventRequest(BaseModel):
    """Everything the engines need to make a decision.

    Free-text fields are length-bounded here and screened again in
    ``security.sanitize_event_request`` before they reach a model.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: EventVertical
    event_name: str = Field(min_length=2, max_length=120)
    host_names: str = Field(default="", max_length=160)
    total_budget: int = Field(ge=1_000, le=100_000_000)
    guest_count: int = Field(ge=5, le=50_000)
    event_date: date
    location_tier: LocationTier
    city: str = Field(min_length=2, max_length=80)
    vibe: str = Field(default="", max_length=200)
    cultural_preferences: str = Field(default="", max_length=500)
    dietary_notes: str = Field(default="", max_length=500)
    custom_notes: str = Field(default="", max_length=1_000)
    priorities: dict[str, int] = Field(default_factory=dict)
    age_group: AgeGroup | None = None
    setting: Setting = Setting.MIXED

    @field_validator("event_date")
    @classmethod
    def date_is_in_window(cls, value: date) -> date:
        """Keep planning dates inside a window the timeline can schedule."""
        today = date.today()
        if value < today - timedelta(days=7):
            raise ValueError("Event date is more than 7 days in the past.")
        if value > today + timedelta(days=365 * 3):
            raise ValueError("Event date must be within 3 years.")
        return value

    @field_validator("guest_count", "total_budget", mode="before")
    @classmethod
    def reject_bool_numbers(cls, value: object) -> object:
        """Booleans are ints in Python. Refuse them so ``true`` is not a budget."""
        if isinstance(value, bool):
            raise ValueError("Numbers must be integers, not booleans.")
        return value

    @field_validator("priorities", mode="before")
    @classmethod
    def priorities_are_scores(cls, value: object) -> dict[str, int]:
        """Accept only known-shaped keys and scores from 1 (low) to 5 (high)."""
        if not isinstance(value, dict):
            raise ValueError("Priorities must be a mapping of category keys to scores.")
        if len(value) > 12:
            raise ValueError("Provide at most 12 priority scores.")
        cleaned: dict[str, int] = {}
        for key, score in value.items():
            if not _PRIORITY_KEY.fullmatch(key):
                raise ValueError(f"Invalid priority key: {key}")
            if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
                raise ValueError(f"Priority for {key} must be an integer from 1 to 5.")
            cleaned[key] = score
        return cleaned


class RebalanceRequest(BaseModel):
    """A what-if change to one category of an existing allocation.

    ``allocations`` is the current plan in rupees. ``new_amount`` replaces
    ``changed_category``. The engine refits every other line and keeps the
    emergency buffer above its floor.
    """

    model_config = ConfigDict(extra="forbid")

    event_type: EventVertical
    total_budget: int = Field(ge=1_000, le=100_000_000)
    guest_count: int = Field(ge=5, le=50_000)
    location_tier: LocationTier
    allocations: dict[str, int]
    changed_category: str = Field(min_length=2, max_length=40)
    new_amount: int = Field(ge=0, le=100_000_000)

    @field_validator("allocations", mode="before")
    @classmethod
    def allocations_are_rupees(cls, value: object) -> dict[str, int]:
        """Reject negative lines and absurd key shapes."""
        if not isinstance(value, dict) or not value or len(value) > 12:
            raise ValueError("Allocations must include the plan categories.")
        for key, amount in value.items():
            if not _PRIORITY_KEY.fullmatch(key):
                raise ValueError(f"Invalid category key: {key}")
            if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
                raise ValueError(f"Amount for {key} must be a non-negative integer.")
        return value


class BudgetLine(BaseModel):
    """One category in the allocation."""

    key: str
    label: str
    amount: int
    percent: float
    per_guest: int | None = None
    critical: bool
    rationale: str


class BudgetPlan(BaseModel):
    """The full money decision, including the notes that justify it."""

    currency: Literal["INR"] = "INR"
    total_budget: int
    guest_count: int
    per_guest_total: int
    lines: list[BudgetLine]
    contingency_amount: int
    warnings: list[str]
    decision_notes: list[str]


class TimelineMilestone(BaseModel):
    """A single scheduled action on the critical path."""

    id: str
    title: str
    phase: str
    due_date: date
    status: Literal["overdue", "due_soon", "scheduled", "event_day"]
    owner: str
    description: str
    critical: bool


class TimelinePlan(BaseModel):
    """Reverse-chronological schedule chosen from how many days remain."""

    event_date: date
    days_remaining: int
    mode: Literal["emergency_sprint", "compressed", "phased"]
    headline: str
    phases: list[str]
    milestones: list[TimelineMilestone]
    warnings: list[str]


class VendorChecklistItem(BaseModel):
    """A vendor or permit to book, with the clauses that usually cause disputes."""

    id: str
    vendor_role: str
    category_key: str
    priority: Literal["critical", "high", "medium", "low"]
    lead_time_days: int
    deposit_percent: int
    book_by: date
    status_hint: str
    contract_clauses: list[str]
    notes: str


class ChecklistPlan(BaseModel):
    """The vendor checklist for this brief."""

    items: list[VendorChecklistItem]
    critical_count: int
    summary: str


class PersonalizedIdea(BaseModel):
    """A concrete concept, not a generic prompt dump."""

    id: str
    title: str
    summary: str
    why_it_fits: str
    effort: Literal["low", "medium", "high"]
    palette: list[str]
    signature_experience: str
    sustainability_tip: str
    source: Literal["rules", "model"]


class CompleteEventPlan(BaseModel):
    """The document the UI renders. Every section is always present."""

    event_name: str
    event_type: EventVertical
    persona_name: str
    persona_summary: str
    city: str
    location_tier: LocationTier
    generated_at: datetime
    decision_mode: Literal["hybrid", "deterministic"]
    provider: str | None
    budget: BudgetPlan
    timeline: TimelinePlan
    checklist: ChecklistPlan
    ideas: list[PersonalizedIdea]
    sustainability_tips: list[str]
    planner_note: str
    assumptions: list[str]


class LlmIdea(BaseModel):
    """Creative fields the model is allowed to write. No money fields."""

    title: str
    summary: str
    why_it_fits: str
    signature_experience: str
    sustainability_tip: str
    palette: list[str]


class VendorClause(BaseModel):
    """One extra contract sentence, matched back onto a checklist role."""

    vendor_role: str
    clause: str


class LlmEnrichment(BaseModel):
    """Structured creative add-on. Amounts and dates stay outside this object."""

    planner_note: str
    ideas: list[LlmIdea]
    extra_contract_clauses: list[VendorClause]
    sustainability_tips: list[str]
