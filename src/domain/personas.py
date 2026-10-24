"""Persona catalog for weddings, birthdays, and community events.

Rule tables live in the vertical modules. This module is what the engines import.
"""

from __future__ import annotations

from src.domain.birthday_persona import build_birthday
from src.domain.community_persona import build_community
from src.domain.persona_specs import (
    CategorySpec,
    Effort,
    EmergencyTemplate,
    IdeaTemplate,
    MilestoneTemplate,
    Persona,
    Priority,
    VendorTemplate,
)
from src.domain.schemas import EventVertical
from src.domain.wedding_persona import build_wedding

__all__ = [
    "CategorySpec",
    "Effort",
    "EmergencyTemplate",
    "IdeaTemplate",
    "MilestoneTemplate",
    "PERSONAS",
    "Persona",
    "Priority",
    "VendorTemplate",
    "get_persona",
    "public_catalog",
]

PERSONAS: dict[EventVertical, Persona] = {
    EventVertical.WEDDING: build_wedding(),
    EventVertical.BIRTHDAY: build_birthday(),
    EventVertical.COMMUNITY: build_community(),
}


def get_persona(vertical: EventVertical | str) -> Persona:
    """Return the rule set for a vertical.

    Args:
        vertical: One of the three challenge personas.

    Returns:
        The matching persona. The dictionary covers every enum value.
    """
    return PERSONAS[EventVertical(vertical)]


def public_catalog() -> list[dict[str, object]]:
    """Return persona metadata the form uses to draw priority sliders.

    Weights are exposed as percents. The server remains the source of truth
    when it allocates money; the UI does not recompute the split.
    """
    catalog: list[dict[str, object]] = []
    for persona in PERSONAS.values():
        catalog.append(
            {
                "event_type": persona.vertical.value,
                "name": persona.name,
                "summary": persona.summary,
                "flagship": persona.vertical is EventVertical.WEDDING,
                "categories": [
                    {
                        "key": category.key,
                        "label": category.label,
                        "base_percent": round(category.base_weight * 100, 1),
                        "critical": category.critical,
                        "adjustable": category.key != persona.contingency_key,
                    }
                    for category in persona.categories
                ],
            }
        )
    return catalog
