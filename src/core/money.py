"""Indian digit grouping for rupee integers.

Both the budget notes and the idea note use this. The walk is O(digits)
and never allocates a list proportional to the amount.
"""


def group_digits(amount: int) -> str:
    """Group the absolute value as Indian digits: 1800000 becomes ``18,00,000``."""
    text = str(abs(amount))
    if len(text) <= 3:
        return text
    head, tail = text[:-3], text[-3:]
    groups: list[str] = []
    while head:
        groups.append(head[-2:])
        head = head[:-2]
    return ",".join(reversed(groups)) + "," + tail


def format_inr(amount: int) -> str:
    """Group digits and keep a leading minus for a negative amount."""
    sign = "-" if amount < 0 else ""
    return sign + group_digits(amount)
