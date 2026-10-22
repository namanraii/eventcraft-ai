"""Domain errors that map to structured JSON responses."""

from __future__ import annotations


class EventCraftError(Exception):
    """Base class for errors the API knows how to present."""

    status_code: int = 400
    code: str = "planner_error"

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        """Store a user-facing message and optional field details.

        Args:
            message: Safe sentence to show in the UI. Must not include secrets.
            details: Short extra lines, such as the field that failed.
        """
        super().__init__(message)
        self.message = message
        self.details = details or []


class PromptInjectionError(EventCraftError):
    """Raised when free text matches a known injection or markup attack."""

    status_code = 400
    code = "unsafe_input"


class PlanInputError(EventCraftError):
    """Raised when a structurally valid payload breaks a planning rule."""

    status_code = 422
    code = "invalid_plan_input"
