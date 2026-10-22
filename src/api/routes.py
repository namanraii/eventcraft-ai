"""HTTP API for plans, what-if rebalancing, and the persona catalog."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.core.cache import ResponseCache, plan_cache_key
from src.core.exceptions import EventCraftError
from src.core.security import sanitize_event_request
from src.domain.personas import public_catalog
from src.domain.schemas import BudgetPlan, CompleteEventPlan, EventRequest, RebalanceRequest
from src.services.budget_engine import BudgetAllocationEngine
from src.services.planner import build_complete_plan

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    """Report liveness, whether a model key is configured, and cache counters."""
    settings = request.app.state.settings
    cache: ResponseCache = request.app.state.cache
    return {
        "status": "ok",
        "service": "eventcraft-ai",
        "version": settings.app_version,
        "llm_configured": settings.active_provider_name() is not None,
        "llm_provider": settings.active_provider_name(),
        "cache": cache.stats(),
        "decision_engines": [
            "BudgetAllocationEngine",
            "TimelineMilestoneGenerator",
            "VendorChecklistManager",
            "PersonalizedIdeaEngine",
        ],
    }


@router.get("/api/v1/personas")
def personas() -> list[dict[str, object]]:
    """Return slider metadata for the three celebration verticals."""
    return public_catalog()


@router.post("/api/v1/plan", response_model=CompleteEventPlan)
async def create_plan(payload: EventRequest, request: Request) -> CompleteEventPlan:
    """Build a full plan. Identical briefs are served from the response cache.

    Free text is screened before it can reach a model. The cache key is the
    cleaned payload, so a repeated brief does not spend another model call.
    """
    clean = sanitize_event_request(payload)
    cache: ResponseCache = request.app.state.cache
    key = plan_cache_key(clean.model_dump(mode="json"))
    cached = cache.get(key)
    if cached is not None:
        return CompleteEventPlan.model_validate(cached)
    plan = await build_complete_plan(clean, request.app.state.orchestrator)
    cache.set(key, plan.model_dump(mode="json"))
    return plan


@router.post("/api/v1/rebalance-budget", response_model=BudgetPlan)
def rebalance_budget(payload: RebalanceRequest) -> BudgetPlan:
    """Refit category amounts after one what-if change. This path does no model call."""
    return BudgetAllocationEngine().rebalance(payload)


def error_response(exc: EventCraftError) -> JSONResponse:
    """Serialize a domain error. The message is safe to show in the page."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
