"""Rule-based concepts for when no model is configured, and as a fallback.

Ideas are chosen by overlap with the brief: age band, setting, and words in
the vibe, culture, and diet notes. The result always names the city and the
guest count so it is not a generic list.
"""

from __future__ import annotations

from collections.abc import Iterable

from src.core.money import group_digits
from src.domain.personas import IdeaTemplate, get_persona
from src.domain.schemas import BudgetPlan, EventRequest, PersonalizedIdea, TimelinePlan


class PersonalizedIdeaEngine:
    """Selects three concepts and a short planner note from the persona library."""

    def compose(
        self,
        request: EventRequest,
        budget: BudgetPlan,
        timeline: TimelinePlan,
    ) -> tuple[list[PersonalizedIdea], list[str], str, list[str]]:
        """Pick ideas and the assumptions that travel with a deterministic plan.

        Args:
            request: The screened brief.
            budget: Already computed. Used only to mention the total in the note.
            timeline: Already computed. Used for the day count and the mode.

        Returns:
            Ideas, sustainability tips, the planner note, and assumptions.
        """
        persona = get_persona(request.event_type)
        brief = _brief_text(request)
        ranked = sorted(
            persona.ideas,
            key=lambda idea: _score(idea, request, brief),
            reverse=True,
        )
        chosen = ranked[:3]
        context = _context(request)
        ideas = [
            PersonalizedIdea(
                id=f"rules-{index}",
                title=idea.title,
                summary=_personalize(idea.summary, context),
                why_it_fits=_personalize(idea.why_it_fits, context),
                effort=idea.effort,
                palette=list(idea.palette),
                signature_experience=idea.signature_experience,
                sustainability_tip=idea.sustainability_tip,
                source="rules",
            )
            for index, idea in enumerate(chosen, start=1)
        ]
        tips = _unique(idea.sustainability_tip for idea in chosen)
        if request.dietary_notes:
            tips.append("Put the dietary note on the caterer contract, not only in a chat message.")
        note = (
            f"{persona.name} built this for {request.event_name} in {request.city}: "
            f"{timeline.days_remaining} days out ({timeline.mode.replace('_', ' ')}), "
            f"₹{group_digits(budget.total_budget)} for {request.guest_count} guests. "
            "The amounts and dates were calculated in code."
        )
        assumptions = [
            "Figures are in INR and are planning allocations, not vendor quotes.",
            "The event date is the main day. Earlier rituals and rehearsals appear as milestones.",
            "The emergency buffer is reserved before priority sliders move any other line.",
            "Per-guest floors are heuristics for Indian metro, city, and destination events.",
            "No model key was used, so ideas and contract tips come from the rule library.",
        ]
        return ideas, tips[:5], note, assumptions


def _brief_text(request: EventRequest) -> str:
    """Lowercase the free-text fields once per request."""
    return " ".join(
        (
            request.vibe,
            request.cultural_preferences,
            request.dietary_notes,
            request.custom_notes,
            request.event_name,
        )
    ).lower()


def _score(idea: IdeaTemplate, request: EventRequest, brief: str) -> int:
    """Score one template. Ties keep the library order because ``sorted`` is stable.

    Keyword checks read the brief that ``compose`` already built, so the
    free-text fields are not joined again for every idea.
    """
    score = 1
    if any(keyword in brief for keyword in idea.keywords):
        score += 3
    if request.age_group is not None and request.age_group.value in idea.age_groups:
        score += 3
    if idea.settings and request.setting.value in idea.settings:
        score += 2
    return score


def _context(request: EventRequest) -> dict[str, str]:
    """Values substituted into idea templates."""
    host = request.host_names.strip() or request.event_name
    return {
        "city": request.city,
        "guests": str(request.guest_count),
        "host": host,
        "event_name": request.event_name,
    }


def _personalize(template: str, context: dict[str, str]) -> str:
    """Fill placeholders. Unknown braces are left untouched by a safe replace."""
    text = template
    for key, value in context.items():
        text = text.replace("{" + key + "}", value)
    return text


def _unique(values: Iterable[str]) -> list[str]:
    """Preserve order while dropping empty and repeated tips."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _group(amount: int) -> str:
    """Format rupees with Indian digit grouping."""
    return group_digits(amount)
