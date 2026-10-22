"""Reverse-chronological schedules driven by the days that remain.

Fewer than 14 days selects an emergency sprint with 48-hour windows.
Fewer than 90 days compresses the persona's phased list and pulls missed
critical work forward. A longer runway keeps the full phase plan.
"""

from __future__ import annotations

from datetime import date, timedelta

from src.domain.personas import EmergencyTemplate, MilestoneTemplate, get_persona
from src.domain.schemas import EventRequest, TimelineMilestone, TimelinePlan


class TimelineMilestoneGenerator:
    """Builds the critical path for one brief."""

    def build(self, request: EventRequest, today: date | None = None) -> TimelinePlan:
        """Choose a scheduling mode and place each milestone on a date.

        Args:
            request: The event brief. Only the vertical and the date are required
                for placement; the persona supplies the task list.
            today: Override for tests. Defaults to the local date.

        Returns:
            A timeline sorted by due date. Status is overdue, due soon,
            scheduled, or event day.
        """
        today = today or date.today()
        persona = get_persona(request.event_type)
        days_remaining = (request.event_date - today).days
        warnings: list[str] = []

        if days_remaining < 14:
            mode = "emergency_sprint"
            milestones = [
                _from_emergency(template, today, request.event_date)
                for template in persona.emergency
            ]
            headline = (
                f"Emergency sprint: {max(days_remaining, 0)} days left. "
                "Booking is collapsed into 48-hour windows."
            )
        elif days_remaining < 90:
            mode = "compressed"
            milestones = _compress(persona.milestones, today, request.event_date, days_remaining)
            headline = (
                f"Compressed plan: {days_remaining} days. "
                "Tasks that no longer fit are pulled into this week, critical ones first."
            )
        else:
            mode = "phased"
            milestones = [_from_phased(template, today, request.event_date) for template in persona.milestones]
            milestones.sort(key=lambda item: (item.due_date, item.title))
            headline = (
                f"Phased plan: {days_remaining} days across concept, vendors, guest logistics, and show day."
            )

        if days_remaining < 0:
            warnings.append("This date is in the past. The list shows what is already late.")
        if request.event_type.value == "community" and days_remaining < 21:
            warnings.append(
                "Public permission often needs several weeks. If an NOC is not already filed, "
                "shrink the footfall or move the date before you announce the event."
            )
        if request.event_type.value == "wedding" and days_remaining < 30:
            warnings.append(
                "A wedding inside 30 days cannot keep every ritual. The sprint keeps the ceremony, the meal, and a cue sheet."
            )

        phases: list[str] = []
        for milestone in milestones:
            if milestone.phase not in phases:
                phases.append(milestone.phase)
        return TimelinePlan(
            event_date=request.event_date,
            days_remaining=days_remaining,
            mode=mode,  # type: ignore[arg-type]
            headline=headline,
            phases=phases,
            milestones=milestones,
            warnings=warnings,
        )


def _status(due: date, today: date, event_date: date) -> str:
    """Classify a due date relative to today and the event."""
    if due == event_date:
        return "event_day"
    if due < today:
        return "overdue"
    if due <= today + timedelta(days=7):
        return "due_soon"
    return "scheduled"


def _clamp(due: date, today: date, event_date: date) -> date:
    """Keep an emergency due date inside the remaining window."""
    if due < today:
        return today
    if due > event_date:
        return event_date
    return due


def _from_phased(template: MilestoneTemplate, today: date, event_date: date) -> TimelineMilestone:
    """Place a template on ``event_date - days_before_event``."""
    due = event_date - timedelta(days=template.days_before_event)
    return TimelineMilestone(
        id=template.id,
        title=template.title,
        phase=template.phase,
        due_date=due,
        status=_status(due, today, event_date),  # type: ignore[arg-type]
        owner=template.owner,
        description=template.description,
        critical=template.critical,
    )


def _from_emergency(template: EmergencyTemplate, today: date, event_date: date) -> TimelineMilestone:
    """Place a sprint task on today or on the event, then clamp it."""
    anchor = today if template.anchor == "start" else event_date
    due = _clamp(anchor + timedelta(days=template.offset_days), today, event_date)
    return TimelineMilestone(
        id=template.id,
        title=template.title,
        phase=template.phase,
        due_date=due,
        status=_status(due, today, event_date),  # type: ignore[arg-type]
        owner=template.owner,
        description=template.description,
        critical=template.critical,
    )


def _compress(
    templates: tuple[MilestoneTemplate, ...],
    today: date,
    event_date: date,
    days_remaining: int,
) -> list[TimelineMilestone]:
    """Keep tasks that still fit, and pull missed critical tasks into this week.

    A template fits when its normal offset is inside the remaining runway
    plus a three-day grace. Critical templates that miss that window are
    staggered one day apart starting today, and their description says they
    are late.
    """
    fitting: list[TimelineMilestone] = []
    late: list[MilestoneTemplate] = []
    for template in templates:
        if template.days_before_event <= days_remaining + 3:
            fitting.append(_from_phased(template, today, event_date))
        elif template.critical:
            late.append(template)
    late.sort(key=lambda template: template.days_before_event, reverse=True)
    pulled: list[TimelineMilestone] = []
    for index, template in enumerate(late):
        due = _clamp(today + timedelta(days=index), today, event_date)
        pulled.append(
            TimelineMilestone(
                id=template.id,
                title=template.title,
                phase=template.phase,
                due_date=due,
                status="due_soon" if due >= today else "overdue",
                owner=template.owner,
                description="This would normally have started earlier. Do it now. " + template.description,
                critical=True,
            )
        )
    combined = pulled + fitting
    combined.sort(key=lambda item: (item.due_date, not item.critical, item.title))
    return _dedupe(combined)


def _dedupe(milestones: list[TimelineMilestone]) -> list[TimelineMilestone]:
    """Drop a repeated id, keeping the earlier due date."""
    seen: set[str] = set()
    unique: list[TimelineMilestone] = []
    for milestone in milestones:
        if milestone.id in seen:
            continue
        seen.add(milestone.id)
        unique.append(milestone)
    return unique
