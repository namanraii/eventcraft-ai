"""Dataclasses for a celebration persona.

The vertical modules hold the rule tables. Engines only read these objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.domain.schemas import AgeGroup, EventVertical, LocationTier, Setting

Priority = Literal["critical", "high", "medium", "low"]
Effort = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class CategorySpec:
    """A budget line and the reason it exists for this persona."""

    key: str
    label: str
    base_weight: float
    critical: bool
    per_guest: bool
    rationale: str


@dataclass(frozen=True)
class MilestoneTemplate:
    """A phased task measured in days before the main event date."""

    id: str
    title: str
    phase: str
    days_before_event: int
    description: str
    owner: str
    critical: bool


@dataclass(frozen=True)
class EmergencyTemplate:
    """A task used only when fewer than 14 days remain.

    ``anchor`` is ``start`` (today) or ``event`` (the event date).
    ``offset_days`` is added to that anchor. Negative offsets land before it.
    """

    id: str
    title: str
    phase: str
    anchor: str
    offset_days: int
    description: str
    owner: str
    critical: bool


@dataclass(frozen=True)
class VendorTemplate:
    """A checklist row. Keyword rows appear only when the brief mentions them."""

    id: str
    vendor_role: str
    category_key: str
    priority: Priority
    lead_time_days: int
    deposit_percent: int
    contract_clauses: tuple[str, ...]
    notes: str
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdeaTemplate:
    """A reusable concept. Placeholders: {city}, {guests}, {host}, {event_name}."""

    title: str
    summary: str
    why_it_fits: str
    effort: Effort
    palette: tuple[str, ...]
    signature_experience: str
    sustainability_tip: str
    keywords: tuple[str, ...] = ()
    age_groups: tuple[str, ...] = ()
    settings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Persona:
    """The full rule set for one vertical."""

    vertical: EventVertical
    name: str
    summary: str
    categories: tuple[CategorySpec, ...]
    contingency_key: str
    contingency_floor: float
    viability_per_guest: dict[LocationTier, int]
    tier_shifts: dict[LocationTier, dict[str, float]]
    tier_shift_notes: dict[LocationTier, str]
    age_shifts: dict[AgeGroup, dict[str, float]]
    age_shift_notes: dict[AgeGroup, str]
    setting_shifts: dict[Setting, dict[str, float]]
    setting_shift_notes: dict[Setting, str]
    milestones: tuple[MilestoneTemplate, ...]
    emergency: tuple[EmergencyTemplate, ...]
    vendors: tuple[VendorTemplate, ...]
    ideas: tuple[IdeaTemplate, ...]
    system_brief: str

    def category(self, key: str) -> CategorySpec:
        """Return one category specification by key."""
        for item in self.categories:
            if item.key == key:
                return item
        raise KeyError(key)

