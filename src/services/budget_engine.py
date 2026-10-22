"""Deterministic budget allocation and what-if rebalancing.

Every rupee is assigned in this module. A model may talk about the result
later, but it cannot change these integers. Category amounts always sum to
``total_budget``.
"""

from __future__ import annotations

from src.core.exceptions import PlanInputError
from src.domain.personas import Persona, get_persona
from src.domain.schemas import (
    BudgetLine,
    BudgetPlan,
    EventRequest,
    LocationTier,
    RebalanceRequest,
)


class BudgetAllocationEngine:
    """Turns a brief into a rupee allocation that sums to the budget."""

    def allocate(self, request: EventRequest) -> BudgetPlan:
        """Apply persona weights, context shifts, and priority sliders.

        Args:
            request: A screened event brief.

        Returns:
            A budget whose line amounts sum to ``request.total_budget``.
        """
        persona = get_persona(request.event_type)
        weights, notes = _adjusted_weights(persona, request)
        amounts = split_amount(request.total_budget, weights)
        amounts = _repair_sum(amounts, request.total_budget, persona.contingency_key)
        return _render(persona, request.total_budget, request.guest_count, request.location_tier, amounts, notes, [])

    def rebalance(self, request: RebalanceRequest) -> BudgetPlan:
        """Refit a plan after one category changes.

        Critical categories keep a larger share of whatever money remains.
        The emergency buffer cannot fall below the persona floor.

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
        total = request.total_budget
        floor = _floor_amount(total, persona.contingency_floor)
        contingency_key = persona.contingency_key
        critical = {category.key for category in persona.categories if category.critical}
        flex_keys = [category.key for category in persona.categories if category.key != contingency_key]
        minimum = max(int(round(total * 0.02)), 0)
        labels = {category.key: category.label for category in persona.categories}
        warnings: list[str] = []
        notes: list[str] = []
        changed = request.changed_category
        requested = request.new_amount

        if changed == contingency_key:
            target = requested
            if target < floor:
                target = floor
                warnings.append(
                    f"The emergency buffer stays at least ₹{_inr(floor)} so a surprise bill does not wipe the plan."
                )
            if minimum and target + minimum * len(flex_keys) > total:
                minimum = 0
            if target > total:
                target = total
                warnings.append("The buffer cannot be larger than the whole budget.")
            distributed = distribute(
                total - target,
                {key: request.allocations[key] for key in flex_keys},
                critical,
                minimum,
            )
            amounts = {**distributed, contingency_key: target}
            notes.append(f"You set {labels[changed]} to ₹{_inr(target)}. The other lines were refit around it.")
        else:
            others = [key for key in flex_keys if key != changed]
            current_buffer = request.allocations.get(contingency_key, floor)
            contingency_amount = max(current_buffer, floor)
            target = requested
            if not _fits(target, contingency_amount, minimum, len(others), total):
                contingency_amount = floor
            if not _fits(target, contingency_amount, minimum, len(others), total):
                minimum = 0
            if not _fits(target, contingency_amount, minimum, len(others), total):
                capped = total - contingency_amount
                warnings.append(
                    f"{labels[changed]} was capped at ₹{_inr(capped)} so the buffer still fits."
                )
                target = max(0, capped)
            distributed = distribute(
                total - target - contingency_amount,
                {key: request.allocations[key] for key in others},
                critical,
                minimum,
            )
            amounts = {**distributed, changed: target, contingency_key: contingency_amount}
            previous = request.allocations.get(changed, 0)
            verb = "increased" if target > previous else "reduced" if target < previous else "kept"
            notes.append(
                f"You {verb} {labels[changed]}. Non-critical lines absorb more of the change. "
                "The emergency buffer stays protected."
            )

        amounts = _repair_sum(amounts, total, contingency_key if changed != contingency_key else changed)
        amounts = _enforce_floor(amounts, contingency_key, floor, critical)
        amounts = _repair_sum(amounts, total, changed if changed != contingency_key else _largest_other(amounts, contingency_key))
        if amounts[contingency_key] < floor:
            amounts = _enforce_floor(amounts, contingency_key, floor, critical)
            amounts = _repair_sum(amounts, total, _largest_other(amounts, contingency_key))
        return _render(
            persona,
            total,
            request.guest_count,
            request.location_tier,
            amounts,
            notes,
            warnings,
        )


def split_amount(total: int, weights: dict[str, float]) -> dict[str, int]:
    """Split an integer total by weights using the largest-remainder method.

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
    critical_keys: set[str],
    minimum: int,
) -> dict[str, int]:
    """Share a rupee pool across categories, protecting critical ones.

    Critical lines receive weight ``current``; other lines receive
    ``current * 0.4``. Each line first receives ``minimum`` rupees when the
    pool can afford that floor.

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
        key: max(current[key], 1) * (1.0 if key in critical_keys else 0.4)
        for key in keys
    }
    shared = split_amount(rest, weights)
    return {key: shared[key] + minimum for key in keys}


def _adjusted_weights(persona: Persona, request: EventRequest) -> tuple[dict[str, float], list[str]]:
    """Fold tier, setting, age, and priority into weights that sum to 1."""
    notes = [f"Started from the {persona.name} baseline."]
    weights = {category.key: category.base_weight for category in persona.categories}
    _apply_shift(weights, persona.tier_shifts.get(request.location_tier, {}), persona.tier_shift_notes.get(request.location_tier), notes)
    _apply_shift(weights, persona.setting_shifts.get(request.setting, {}), persona.setting_shift_notes.get(request.setting), notes)
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
        score = request.priorities.get(key, 3)
        raw[key] = weights[key] * (score / 3.0)
        if key in request.priorities and score != 3:
            direction = "up" if score > 3 else "down"
            notes.append(f"{labels[key]} is set to {score} of 5, so its share moves {direction} from the baseline.")
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
    if any(value < 0.01 for value in proposed.values()):
        notes.append("A context shift was skipped because a category would have dropped below 1 percent.")
        return
    if abs(sum(proposed.values()) - 1.0) > 0.02:
        return
    weights.update(proposed)
    if note:
        notes.append(note)


def _render(
    persona: Persona,
    total: int,
    guest_count: int,
    tier: LocationTier,
    amounts: dict[str, int],
    notes: list[str],
    warnings: list[str],
) -> BudgetPlan:
    """Build the response model and add viability warnings."""
    warnings = list(warnings)
    notes = list(notes)
    percents = _percents(amounts, total)
    lines: list[BudgetLine] = []
    per_guest_amount: int | None = None
    per_guest_label = ""
    for category in persona.categories:
        amount = amounts[category.key]
        per_guest = int(amount / guest_count) if category.per_guest else None
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
    threshold = persona.viability_per_guest[tier]
    if per_guest_amount is not None and per_guest_amount < threshold:
        warnings.append(
            f"{per_guest_label} is ₹{_inr(per_guest_amount)} per guest. "
            f"A workable {tier.value} {persona.vertical.value} is usually at least "
            f"₹{_inr(threshold)} for that line. Shrink the guest list, simplify the menu, "
            "or move money here before you sign a caterer."
        )
    elif per_guest_amount is not None and per_guest_amount > threshold * 3:
        notes.append(
            f"{per_guest_label} is ₹{_inr(per_guest_amount)} per guest, well above the "
            f"{tier.value} planning floor of ₹{_inr(threshold)}. You have room to add a comfort, not a second theme."
        )
    return BudgetPlan(
        total_budget=total,
        guest_count=guest_count,
        per_guest_total=int(total / guest_count),
        lines=lines,
        contingency_amount=amounts[persona.contingency_key],
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
        donors = sorted((key for key in repaired if key != sink), key=lambda key: repaired[key], reverse=True)
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
    critical: set[str],
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
    repaired[contingency_key] = repaired.get(contingency_key, 0) + (floor - repaired.get(contingency_key, 0) - gap)
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


def _inr(amount: int) -> str:
    """Format a rupee integer with Indian grouping."""
    sign = "-" if amount < 0 else ""
    text = str(abs(amount))
    if len(text) <= 3:
        return sign + text
    head, tail = text[:-3], text[-3:]
    groups: list[str] = []
    while head:
        groups.append(head[-2:])
        head = head[:-2]
    return sign + ",".join(reversed(groups)) + "," + tail
