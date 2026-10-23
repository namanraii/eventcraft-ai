"""Context-aware vendor checklist and booking-window scorer.

Lead time is measured backward from the event date. A window that has already
closed is marked so, and a high-priority row is raised to critical. Keyword
rows, such as mehendi, appear only when the brief mentions them.
"""

from __future__ import annotations

from datetime import date, timedelta

from src.domain.personas import Priority, VendorTemplate, get_persona
from src.domain.schemas import ChecklistPlan, EventRequest, VendorChecklistItem


class VendorChecklistManager:
    """Builds the vendor and permit list for one brief."""

    def build(self, request: EventRequest, today: date | None = None) -> ChecklistPlan:
        """Select vendors and score each booking window.

        Args:
            request: The screened brief. Free text selects optional rows.
            today: Override for tests.

        Returns:
            A checklist sorted by priority, then by the book-by date.
        """
        today = today or date.today()
        persona = get_persona(request.event_type)
        haystack = _haystack(request)
        selected = [vendor for vendor in persona.vendors if _matches(vendor, haystack)]
        items = [_score(vendor, request.event_date, today) for vendor in selected]
        rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda item: (rank[item.priority], item.book_by, item.vendor_role))
        critical_count = sum(1 for item in items if item.priority == "critical")
        late_count = sum(1 for item in items if item.status_hint.startswith("Lead time"))
        summary = (
            f"{len(items)} vendors or permits, {critical_count} of them critical. "
            f"{late_count} already past a normal lead time."
        )
        return ChecklistPlan(items=items, critical_count=critical_count, summary=summary)


def _haystack(request: EventRequest) -> str:
    """Join the free-text fields the keyword rules read."""
    parts = (
        request.event_name,
        request.host_names,
        request.vibe,
        request.cultural_preferences,
        request.dietary_notes,
        request.custom_notes,
        request.city,
    )
    return " ".join(parts).lower()


def _matches(vendor: VendorTemplate, haystack: str) -> bool:
    """Keep a vendor with no keywords, or one whose keyword appears in the brief."""
    if not vendor.keywords:
        return True
    return any(keyword in haystack for keyword in vendor.keywords)


def _score(vendor: VendorTemplate, event_date: date, today: date) -> VendorChecklistItem:
    """Attach a book-by date and a plain-language hint."""
    book_by = event_date - timedelta(days=vendor.lead_time_days)
    priority: Priority = vendor.priority
    if book_by < today:
        hint = "Lead time has passed. Call today and ask what can still be delivered."
        if priority in {"high", "medium"}:
            priority = "critical"
    elif book_by <= today + timedelta(days=7):
        hint = "Book this week. Ask for the deposit terms before you hold the date."
    else:
        hint = f"On track if you book by {book_by.strftime('%d %b %Y')}."
    return VendorChecklistItem(
        id=vendor.id,
        vendor_role=vendor.vendor_role,
        category_key=vendor.category_key,
        priority=priority,
        lead_time_days=vendor.lead_time_days,
        deposit_percent=vendor.deposit_percent,
        book_by=book_by,
        status_hint=hint,
        contract_clauses=list(vendor.contract_clauses),
        notes=vendor.notes,
    )
