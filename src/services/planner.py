"""Compose the four engines, then optionally enrich the creative sections.

Money, dates, and the checklist structure are fixed before the model runs.
A model failure leaves the deterministic plan intact.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from src.domain.personas import get_persona
from src.domain.schemas import (
    ChecklistPlan,
    CompleteEventPlan,
    EventRequest,
    PersonalizedIdea,
    VendorChecklistItem,
    VendorClause,
)
from src.services.budget_engine import BudgetAllocationEngine
from src.services.checklist_engine import VendorChecklistManager
from src.services.idea_engine import PersonalizedIdeaEngine
from src.services.llm_orchestrator import EnrichmentResult, LlmOrchestrator
from src.services.timeline_engine import TimelineMilestoneGenerator

logger = logging.getLogger(__name__)


async def build_complete_plan(
    request: EventRequest,
    orchestrator: LlmOrchestrator,
    today: date | None = None,
) -> CompleteEventPlan:
    """Run every engine and return one plan document.

    Args:
        request: A brief that has already been screened.
        orchestrator: Model client. It may have zero providers configured.
        today: Clock override for tests.

    Returns:
        A complete plan. ``decision_mode`` is ``hybrid`` only when the model
        returned at least two usable ideas.
    """
    budget = BudgetAllocationEngine().allocate(request)
    timeline = TimelineMilestoneGenerator().build(request, today=today)
    checklist = VendorChecklistManager().build(request, today=today)
    ideas, tips, note, assumptions = PersonalizedIdeaEngine().compose(request, budget, timeline)
    persona = get_persona(request.event_type)
    provider: str | None = None
    decision_mode = "deterministic"

    enrichment = await _safe_enrich(orchestrator, request, budget, timeline, checklist)
    if enrichment is not None:
        model_ideas = _ideas_from_model(enrichment)
        if len(model_ideas) >= 2:
            ideas = model_ideas
            decision_mode = "hybrid"
            provider = enrichment.provider
            if enrichment.payload.planner_note:
                note = enrichment.payload.planner_note
            tips = _merge_tips(tips, enrichment.payload.sustainability_tips)
            checklist = _merge_clauses(checklist, enrichment.payload.extra_contract_clauses)
            assumptions = [item for item in assumptions if not item.startswith("No model key")]
            assumptions.append(
                "Creative ideas were drafted by the configured model. "
                "Amounts, dates, and the checklist structure still come from the deterministic engines."
            )

    return CompleteEventPlan(
        event_name=request.event_name,
        event_type=request.event_type,
        persona_name=persona.name,
        persona_summary=persona.summary,
        city=request.city,
        location_tier=request.location_tier,
        generated_at=datetime.now(timezone.utc),
        decision_mode=decision_mode,  # type: ignore[arg-type]
        provider=provider,
        budget=budget,
        timeline=timeline,
        checklist=checklist,
        ideas=ideas,
        sustainability_tips=tips,
        planner_note=note,
        assumptions=assumptions,
    )


async def _safe_enrich(orchestrator: LlmOrchestrator, request: EventRequest, budget, timeline, checklist):  # type: ignore[no-untyped-def]
    """Call the orchestrator and swallow unexpected failures."""
    try:
        return await orchestrator.enrich(request, budget, timeline, checklist)
    except Exception:
        logger.warning("Enrichment failed; the rule library will be used.")
        return None


def _ideas_from_model(enrichment: EnrichmentResult) -> list[PersonalizedIdea]:
    """Map model ideas into the public idea shape. Effort stays medium."""
    ideas: list[PersonalizedIdea] = []
    for index, idea in enumerate(enrichment.payload.ideas, start=1):
        palette = [color.strip()[:40] for color in idea.palette if color.strip()][:4]
        ideas.append(
            PersonalizedIdea(
                id=f"model-{index}",
                title=idea.title.strip()[:120],
                summary=idea.summary.strip()[:500],
                why_it_fits=idea.why_it_fits.strip()[:500],
                effort="medium",
                palette=palette or ["ivory", "ink", "brass"],
                signature_experience=idea.signature_experience.strip()[:300],
                sustainability_tip=idea.sustainability_tip.strip()[:300],
                source="model",
            )
        )
    return ideas


def _merge_tips(rule_tips: list[str], model_tips: list[str]) -> list[str]:
    """Prefer model tips, then fill with rule tips, capped at five."""
    merged: list[str] = []
    for tip in list(model_tips) + list(rule_tips):
        text = tip.strip()
        if text and text not in merged:
            merged.append(text)
    return merged[:5]


def _merge_clauses(checklist: ChecklistPlan, clauses: list[VendorClause]) -> ChecklistPlan:
    """Append model clauses onto the matching vendor, capped at six each."""
    updated: list[VendorChecklistItem] = []
    for item in checklist.items:
        role = item.vendor_role.lower()
        extra: list[str] = []
        for clause in clauses:
            target = clause.vendor_role.lower().strip()
            text = clause.clause.strip()[:240]
            if not text or not target:
                continue
            if target == role or target in role or role in target:
                if text not in item.contract_clauses and text not in extra:
                    extra.append(text)
        updated.append(item.model_copy(update={"contract_clauses": (item.contract_clauses + extra)[:6]}))
    return checklist.model_copy(update={"items": updated})
