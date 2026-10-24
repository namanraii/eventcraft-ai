"""Deterministic budget allocation and what-if rebalancing.

Every rupee is assigned in this module. A model may talk about the result
later, but it cannot change these integers. Category amounts always sum to
``total_budget``.

The split is the largest-remainder method: O(C log C) time and O(C) extra
space for C categories. Nothing here loops over rupees or guests.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.exceptions import PlanInputError
from src.core.money import format_inr
from src.domain.bounds import (
    COMFORT_MULTIPLE,
    LINE_FLOOR_RATIO,
    MIN_CATEGORY_WEIGHT,
    NON_CRITICAL_WEIGHT,
    PRIORITY_NEUTRAL,
    SHIFT_SUM_TOLERANCE,
)
from src.domain.personas import Persona, get_persona
from src.domain.schemas import (
    BudgetLine,
    BudgetPlan,
    EventRequest,
    LocationTier,
    RebalanceRequest,
)


@dataclass(frozen=True)
class _AllocationView:
    """Everything the renderer needs. Keeping it one object shortens the call."""

    persona: Persona
    total: int
    guest_count: int
    tier: LocationTier
    amounts: dict[str, int]
    notes: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class _LineFacts:
    """Category facts for one what-if, collected in a single pass."""

    total: int
    floor: int
    contingency_key: str
    critical: frozenset[str]
    flex_keys: tuple[str, ...]
    labels: dict[str, str]
    minimum: int
    changed: str
    requested: int


class BudgetAllocationEngine:
    """Turns a brief into a rupee allocation that sums to the budget."""

    def allocate(self, request: EventRequest) -> BudgetPlan:
        """Apply persona weights, context shifts, and priority sliders.

        One pass adjusts the weights. One apportionment assigns the rupees.
        Time is O(C log C). Space is O(C).

        Args:
            request: A screened event brief.

        Returns:
            A budget whose line amounts sum to ``request.total_budget``.
        """
        persona = get_persona(request.event_type)
        weights, notes = _adjusted_weights(persona, request)
        amounts = split_amount(request.total_budget, weights)
        amounts = _repair_sum(amounts, request.total_budget, persona.contingency_key)
        return _render(
            _AllocationView(
                persona=persona,
                total=request.total_budget,
                guest_count=request.guest_count,
                tier=request.location_tier,
                amounts=amounts,
                notes=notes,
                warnings=[],
            )
        )

    def rebalance(self, request: RebalanceRequest) -> BudgetPlan:
        """Refit a plan after one category changes.

        Critical categories keep a larger share of whatever money remains.
        The emergency buffer cannot fall below the persona floor.
        Aside from the apportionment sort, the refit is linear in C.

        Args:
            request: Current allocations plus the category to replace.

        Returns:
            A new budget that still sums to the original total.

        Raises:
            PlanInputError: If the categories do not match the persona, or
                the current lines do not sum to the total.
        """
        persona = get_persona(request.event_type)
        _validate_allocations(persona, request)
        facts = _line_facts(persona, request)
        if facts.changed == facts.contingency_key:
            amounts, notes, warnings = _refit_around_buffer(facts, request)
        else:
            amounts, notes, warnings = _refit_around_line(facts, request)
        return _render(
            _AllocationView(
                persona=persona,
                total=facts.total,
                guest_count=request.guest_count,
                tier=request.location_tier,
                amounts=_settle(amounts, facts),
                notes=notes,
                warnings=warnings,
            )
        )


def _line_facts(persona: Persona, request: RebalanceRequest) -> _LineFacts:
    """Read each category once and return the facts the refit shares."""
    total = request.total_budget
    contingency_key = persona.contingency_key
    categories = persona.categories
    return _LineFacts(
        total=total,
        floor=_floor_amount(total, persona.contingency_floor),
        contingency_key=contingency_key,
        critical=frozenset(category.key for category in categories if category.critical),
        flex_keys=tuple(category.key for category in categories if category.key != contingency_key),
        labels={category.key: category.label for category in categories},
        minimum=max(int(round(total * LINE_FLOOR_RATIO)), 0),
        changed=request.changed_category,
        requested=request.new_amount,
    )


def _refit_around_buffer(
    facts: _LineFacts,
    request: RebalanceRequest,
) -> tuple[dict[str, int], list[str], list[str]]:
    """Refit the flexible lines around a new emergency buffer."""
    warnings: list[str] = []
    notes: list[str] = []
    target = facts.requested
    if target < facts.floor:
        target = facts.floor
        warnings.append(
            f"The emergency buffer stays at least ₹{format_inr(facts.floor)} "
            "so a surprise bill does not wipe the plan."
        )
    minimum = facts.minimum
    if minimum and target + minimum * len(facts.flex_keys) > facts.total:
        minimum = 0
    if target > facts.total:
        target = facts.total
        warnings.append("The buffer cannot be larger than the whole budget.")
    distributed = distribute(
        facts.total - target,
        {key: request.allocations[key] for key in facts.flex_keys},
        facts.critical,
        minimum,
    )
    amounts = {**distributed, facts.contingency_key: target}
    notes.append(
        f"You set {facts.labels[facts.changed]} to ₹{format_inr(target)}. "
        "The other lines were refit around it."
    )
    return amounts, notes, warnings


def _refit_around_line(
    facts: _LineFacts,
    request: RebalanceRequest,
) -> tuple[dict[str, int], list[str], list[str]]:
    """Lock one flexible line and share what remains, protecting the buffer."""
    warnings: list[str] = []
    notes: list[str] = []
    others = [key for key in facts.flex_keys if key != facts.changed]
    current_buffer = request.allocations.get(facts.contingency_key, facts.floor)
    contingency_amount = max(current_buffer, facts.floor)
    target = facts.requested
    minimum = facts.minimum
    if not _fits(target, contingency_amount, minimum, len(others), facts.total):
        contingency_amount = facts.floor
    if not _fits(target, contingency_amount, minimum, len(others), facts.total):
        minimum = 0
    if not _fits(target, contingency_amount, minimum, len(others), facts.total):
        capped = facts.total - contingency_amount
        warnings.append(
            f"{facts.labels[facts.changed]} was capped at ₹{format_inr(capped)} "
            "so the buffer still fits."
        )
        target = max(0, capped)
    distributed = distribute(
        facts.total - target - contingency_amount,
        {key: request.allocations[key] for key in others},
        facts.critical,
        minimum,
    )
    amounts = {**distributed, facts.changed: target, facts.contingency_key: contingency_amount}
    previous = request.allocations.get(facts.changed, 0)
    verb = "increased" if target > previous else "reduced" if target < previous else "kept"
    notes.append(
        f"You {verb} {facts.labels[facts.changed]}. Non-critical lines absorb more of the change. "
        "The emergency buffer stays protected."
    )
    return amounts, notes, warnings


def _settle(amounts: dict[str, int], facts: _LineFacts) -> dict[str, int]:
    """Push rounding drift, then put the buffer back on its floor.

    The second floor check covers a repair that borrowed the buffer itself.
    """
    changed = facts.changed
    contingency_key = facts.contingency_key
    sink = contingency_key if changed != contingency_key else changed
    repaired = _repair_sum(amounts, facts.total, sink)
    repaired = _enforce_floor(repaired, contingency_key, facts.floor, facts.critical)
    other = changed if changed != contingency_key else _largest_other(repaired, contingency_key)
    repaired = _repair_sum(repaired, facts.total, other)
    if repaired[contingency_key] < facts.floor:
        repaired = _enforce_floor(repaired, contingency_key, facts.floor, facts.critical)
        repaired = _repair_sum(repaired, facts.total, _largest_other(repaired, contingency_key))
    return repaired


def split_amount(total: int, weights: dict[str, float]) -> dict[str, int]:
    """Split an integer total by the largest-remainder method.

    Time is O(C log C) for the remainder sort. Space is O(C). An equal
    remainder goes to the later key, so the same weights always produce
    the same rupees.

    Args:
        total: Rupees to assign. Must be non-negative.
        weights: Non-negative weights. They do not need to sum to 1.

    Returns:
        Integer amounts that sum to ``total``.
    """
    if total < 0:
        raise ValueError("total must be non-negative")
    if not weights:
        return {}
    clean = {key: max(float(weight), 0.0) for key, weight in weights.items()}
    weight_sum = sum(clean.values())
    if weight_sum <= 0:
        clean = {key: 1.0 for key in weights}
        weight_sum = float(len(clean))
    raw = {key: total * (weight / weight_sum) for key, weight in clean.items()}
    floors = {key: int(raw[key]) for key in raw}
    left = total - sum(floors.values())
    order = sorted(raw, key=lambda key: (raw[key] - floors[key], key), reverse=True)
    for key in order:
        if left <= 0:
            break
        floors[key] += 1
        left -= 1
    return floors


def distribute(
    pool: int,
    current: dict[str, int],
    critical_keys: frozenset[str] | set[str],
    minimum: int,
) -> dict[str, int]:
    """Share a rupee pool across categories, protecting critical ones.

    Critical lines receive weight ``current``; other lines receive
    ``current`` times ``NON_CRITICAL_WEIGHT``. Each line first receives
    ``minimum`` rupees when the pool can afford that floor. The weighted
    part is one largest-remainder split, so this is O(C log C).

    Args:
        pool: Rupees available for these categories.
        current: Current amounts, used as relative weights.
        critical_keys: Keys that should keep more of the pool.
        minimum: Per-category floor. Dropped to zero if it cannot fit.

    Returns:
        Amounts that sum to ``pool``.
    """
    keys = list(current)
    if not keys:
        return {}
    pool = max(pool, 0)
    minimum = max(minimum, 0)
    if minimum * len(keys) > pool:
        minimum = 0
    rest = pool - minimum * len(keys)
    weights = {
        key: max(current[key], 1) * (1.0 if key in critical_keys else NON_CRITICAL_WEIGHT)
        for key in keys
    }
    shared = split_amount(rest, weights)
    return {key: shared[key] + minimum for key in keys}


def _adjusted_weights(
    persona: Persona, request: EventRequest
) -> tuple[dict[str, float], list[str]]:
    """Fold tier, setting, age, and priority into weights that sum to 1."""
    notes = [f"Started from the {persona.name} baseline."]
    weights = {category.key: category.base_weight for category in persona.categories}
    _apply_shift(
        weights,
        persona.tier_shifts.get(request.location_tier, {}),
        persona.tier_shift_notes.get(request.location_tier),
        notes,
    )
    _apply_shift(
        weights,
        persona.setting_shifts.get(request.setting, {}),
        persona.setting_shift_notes.get(request.setting),
        notes,
    )
    if request.event_type.value == "birthday" and request.age_group is not None:
        _apply_shift(
            weights,
            persona.age_shifts.get(request.age_group, {}),
            persona.age_shift_notes.get(request.age_group),
            notes,
        )

    contingency_key = persona.contingency_key
    contingency = weights[contingency_key]
    flex_keys = [key for key in weights if key != contingency_key]
    raw: dict[str, float] = {}
    labels = {category.key: category.label for category in persona.categories}
    for key in flex_keys:
        score = request.priorities.get(key, PRIORITY_NEUTRAL)
        raw[key] = weights[key] * (score / PRIORITY_NEUTRAL)
        if key in request.priorities and score != PRIORITY_NEUTRAL:
            direction = "up" if score > PRIORITY_NEUTRAL else "down"
            notes.append(
                f"{labels[key]} is set to {score} of 5, "
                f"so its share moves {direction} from the baseline."
            )
    flex_target = 1.0 - contingency
    raw_sum = sum(raw.values()) or 1.0
    for key in flex_keys:
        weights[key] = flex_target * raw[key] / raw_sum
    weights[contingency_key] = contingency
    return weights, notes


def _apply_shift(
    weights: dict[str, float],
    delta: dict[str, float],
    note: str | None,
    notes: list[str],
) -> None:
    """Add a zero-sum shift, then keep every weight at or above 1 percent."""
    if not delta:
        return
    proposed = dict(weights)
    for key, change in delta.items():
        if key not in proposed:
            return
        proposed[key] = proposed[key] + change
    if any(value < MIN_CATEGORY_WEIGHT for value in proposed.values()):
        notes.append(
            "A context shift was skipped because a category would have dropped below 1 percent."
        )
        return
    if abs(sum(proposed.values()) - 1.0) > SHIFT_SUM_TOLERANCE:
        return
    weights.update(proposed)
    if note:
        notes.append(note)


def _render(view: _AllocationView) -> BudgetPlan:
    """Build the response model and add viability warnings."""
    warnings = list(view.warnings)
    notes = list(view.notes)
    percents = _percents(view.amounts, view.total)
    lines: list[BudgetLine] = []
    per_guest_amount: int | None = None
    per_guest_label = ""
    for category in view.persona.categories:
        amount = view.amounts[category.key]
        per_guest = int(amount / view.guest_count) if category.per_guest else None
        if category.per_guest:
            per_guest_amount = per_guest
            per_guest_label = category.label
        lines.append(
            BudgetLine(
                key=category.key,
                label=category.label,
                amount=amount,
                percent=percents[category.key],
                per_guest=per_guest,
                critical=category.critical,
                rationale=category.rationale,
            )
        )
    threshold = view.persona.viability_per_guest[view.tier]
    if per_guest_amount is not None and per_guest_amount < threshold:
        warnings.append(
            f"{per_guest_label} is ₹{format_inr(per_guest_amount)} per guest. "
            f"A workable {view.tier.value} {view.persona.vertical.value} is usually at least "
            f"₹{format_inr(threshold)} for that line. Shrink the guest list, simplify the menu, "
            "or move money here before you sign a caterer."
        )
    elif per_guest_amount is not None and per_guest_amount > threshold * COMFORT_MULTIPLE:
        notes.append(
            f"{per_guest_label} is ₹{format_inr(per_guest_amount)} per guest, well above the "
            f"{view.tier.value} planning floor of ₹{format_inr(threshold)}. "
            "You have room to add a comfort, not a second theme."
        )
    return BudgetPlan(
        total_budget=view.total,
        guest_count=view.guest_count,
        per_guest_total=int(view.total / view.guest_count),
        lines=lines,
        contingency_amount=view.amounts[view.persona.contingency_key],
        warnings=warnings,
        decision_notes=notes,
    )


def _percents(amounts: dict[str, int], total: int) -> dict[str, float]:
    """Round percents to one decimal and pin the largest line so they sum to 100."""
    if total <= 0:
        return {key: 0.0 for key in amounts}
    rounded = {key: round(amount / total * 100, 1) for key, amount in amounts.items()}
    drift = round(100.0 - sum(rounded.values()), 1)
    if rounded and drift != 0:
        sink = max(rounded, key=lambda key: (amounts[key], key))
        rounded[sink] = round(rounded[sink] + drift, 1)
    return rounded


def _repair_sum(amounts: dict[str, int], total: int, sink: str) -> dict[str, int]:
    """Push rounding drift into one category, then borrow if that goes negative."""
    repaired = dict(amounts)
    repaired[sink] = repaired.get(sink, 0) + (total - sum(repaired.values()))
    if repaired[sink] < 0:
        debt = -repaired[sink]
        repaired[sink] = 0
        donors = sorted(
            (key for key in repaired if key != sink),
            key=lambda key: repaired[key],
            reverse=True,
        )
        for key in donors:
            take = min(debt, repaired[key])
            repaired[key] -= take
            debt -= take
            if debt == 0:
                break
    return repaired


def _enforce_floor(
    amounts: dict[str, int],
    contingency_key: str,
    floor: int,
    critical: frozenset[str] | set[str],
) -> dict[str, int]:
    """Raise the buffer to its floor by taking from non-critical lines first."""
    repaired = dict(amounts)
    gap = floor - repaired.get(contingency_key, 0)
    if gap <= 0:
        return repaired
    donors = sorted(
        (key for key in repaired if key != contingency_key),
        key=lambda key: (key in critical, -repaired[key]),
    )
    for key in donors:
        take = min(gap, repaired[key])
        repaired[key] -= take
        gap -= take
        if gap == 0:
            break
    current = repaired.get(contingency_key, 0)
    repaired[contingency_key] = current + (floor - current - gap)
    return repaired


def _floor_amount(total: int, ratio: float) -> int:
    """Convert a ratio floor into rupees."""
    return int(round(total * ratio))


def _fits(target: int, contingency: int, minimum: int, others: int, total: int) -> bool:
    """Return whether a locked amount still leaves room for the rest."""
    return target >= 0 and target + contingency + minimum * others <= total


def _largest_other(amounts: dict[str, int], skip: str) -> str:
    """Return the largest category that is not ``skip``."""
    others = [key for key in amounts if key != skip]
    if not others:
        return skip
    return max(others, key=lambda key: amounts[key])


def _validate_allocations(persona: Persona, request: RebalanceRequest) -> None:
    """Check that the what-if payload matches this persona's categories."""
    expected = {category.key for category in persona.categories}
    received = set(request.allocations)
    if received != expected:
        missing = sorted(expected - received)
        unknown = sorted(received - expected)
        raise PlanInputError(
            "The allocation does not match this celebration's categories.",
            details=[f"missing={','.join(missing)}", f"unknown={','.join(unknown)}"],
        )
    if request.changed_category not in expected:
        raise PlanInputError(
            "That category is not part of this celebration.",
            details=[request.changed_category],
        )
    if sum(request.allocations.values()) != request.total_budget:
        raise PlanInputError(
            "Current allocations must add up to the total budget before a what-if change.",
            details=[f"sum={sum(request.allocations.values())}", f"total={request.total_budget}"],
        )
