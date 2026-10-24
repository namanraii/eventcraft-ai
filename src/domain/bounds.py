"""Planning thresholds the engines share.

The numbers are part of the persona contract. Naming them keeps a mode
boundary from drifting between the timeline, the checklist, and the schema.
"""

EMERGENCY_RUNWAY_DAYS = 14
COMPRESSED_RUNWAY_DAYS = 90
DUE_SOON_DAYS = 7
COMMUNITY_PERMIT_DAYS = 21
WEDDING_SHORT_RUNWAY_DAYS = 30
COMPRESS_GRACE_DAYS = 3
PAST_DATE_GRACE_DAYS = 7
PLANNING_HORIZON_DAYS = 365 * 3

# A flexible line is offered this share of the budget before weights are applied.
LINE_FLOOR_RATIO = 0.02
# Non-critical lines keep this fraction of their current amount as weight.
NON_CRITICAL_WEIGHT = 0.4
# A context shift that would push any category under this weight is rejected.
MIN_CATEGORY_WEIGHT = 0.01
# A shift whose weights no longer sum near 1 is not zero-sum, so it is rejected.
SHIFT_SUM_TOLERANCE = 0.02
# Priority 3 is the persona baseline. Sliders run from 1 to 5.
PRIORITY_NEUTRAL = 3
# A per-guest cost above this multiple of the viability floor is noted as comfortable.
COMFORT_MULTIPLE = 3
