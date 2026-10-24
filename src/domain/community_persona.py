"""Community-event rule tables.

The builder only assembles these tables."""

from __future__ import annotations

from src.domain.persona_specs import (
    CategorySpec,
    EmergencyTemplate,
    IdeaTemplate,
    MilestoneTemplate,
    Persona,
    VendorTemplate,
)
from src.domain.schemas import EventVertical, LocationTier, Setting

_COMMUNITY_CATEGORIES = (
    CategorySpec(
        "venue_permits",
        "Venue, permits, and NOC",
        0.18,
        True,
        False,
        "A crowd you cannot legally host is not a plan. Permissions are a budget line.",
    ),
    CategorySpec(
        "stage_sound",
        "Stage, sound, and power",
        0.16,
        True,
        False,
        "People leave when they cannot hear, or when the generator fails.",
    ),
    CategorySpec(
        "catering",
        "Refreshments and water",
        0.22,
        True,
        True,
        "Water and a simple snack are a safety item at this footfall, not a luxury.",
    ),
    CategorySpec(
        "safety",
        "Safety and crowd management",
        0.12,
        True,
        False,
        "Barricades, a medical corner, and named marshals sit above signage.",
    ),
    CategorySpec(
        "outreach",
        "Outreach and signage",
        0.08,
        False,
        False,
        "Tell people the hours and the entry plan. Do not advertise a crowd you cannot hold.",
    ),
    CategorySpec(
        "volunteers",
        "Volunteer operations",
        0.10,
        False,
        False,
        "Shifts, water, and a lead on the radio. Volunteers are an operation, not a favour.",
    ),
    CategorySpec(
        "contingency",
        "Contingency reserve",
        0.14,
        True,
        False,
        "Municipal events overrun on power, water, and last-minute compliance. The reserve is "
        "larger on purpose.",
    ),
)


_COMMUNITY_MILESTONES = (
    MilestoneTemplate(
        "brief",
        "Fix footfall, budget, and the sponsor gap",
        "Permissions and site",
        90,
        "Write the maximum footfall you will allow. Sponsorship reduces the gap; it does not "
        "raise the cap.",
        "Committee",
        True,
    ),
    MilestoneTemplate(
        "permits",
        "File municipal permission, NOC, and police intimation",
        "Permissions and site",
        75,
        "Start this before you print a poster. If the window has closed, shrink the event.",
        "Committee",
        True,
    ),
    MilestoneTemplate(
        "site",
        "Confirm site, power, water, and toilets",
        "Permissions and site",
        60,
        "Count drinking points and toilets against the footfall, not against hope.",
        "Logistics lead",
        True,
    ),
    MilestoneTemplate(
        "stage",
        "Book stage, sound, and a power plan",
        "Production",
        45,
        "A quiet generator test is part of the booking, not an extra.",
        "Production lead",
        True,
    ),
    MilestoneTemplate(
        "safety",
        "Safety plan, medical, and insurance",
        "Production",
        40,
        "Barricades, a fire extinguisher point, a first-aid corner, and a written weather "
        "call.",
        "Safety lead",
        True,
    ),
    MilestoneTemplate(
        "crew",
        "Publish volunteer shifts",
        "People and outreach",
        30,
        "Three-hour shifts with a named lead. No one works the full day unpaid and unfed.",
        "Volunteer lead",
        True,
    ),
    MilestoneTemplate(
        "food",
        "Confirm water and food stalls",
        "People and outreach",
        21,
        "Drinking water is free. Food vendors follow the same allergen and waste rules.",
        "Logistics lead",
        True,
    ),
    MilestoneTemplate(
        "outreach",
        "Outreach with the real entry plan",
        "People and outreach",
        14,
        "Publish hours, the gate plan, and what is free. Correct the footfall if permission "
        "came back lower.",
        "Outreach lead",
        False,
    ),
    MilestoneTemplate(
        "dry-run",
        "Dry run and vendor confirmations",
        "Show day",
        7,
        "Walk the gate, the stage cue, and the medical path.",
        "Committee",
        True,
    ),
    MilestoneTemplate(
        "briefing",
        "Marshal briefing",
        "Show day",
        2,
        "Radios, the lost-person point, and who is allowed to stop the show.",
        "Safety lead",
        True,
    ),
    MilestoneTemplate(
        "day",
        "Show day crowd plan",
        "Show day",
        0,
        "Open gates on time, count entries, and pause entry if you hit the permitted footfall.",
        "Committee",
        True,
    ),
)


_COMMUNITY_EMERGENCY = (
    EmergencyTemplate(
        "legal",
        "Check whether the gathering is still lawful",
        "Emergency sprint",
        "start",
        0,
        "If a permit or NOC is required and not filed, reduce footfall to a private meeting or "
        "move the date. Do not advertise a crowd you cannot host.",
        "Committee",
        True,
    ),
    EmergencyTemplate(
        "cap",
        "Publish a hard footfall cap",
        "Emergency sprint",
        "start",
        0,
        "Pick a number the site can hold with water and a medical corner. Staff the gate to "
        "that number.",
        "Committee",
        True,
    ),
    EmergencyTemplate(
        "site",
        "Secure power, water, and a first-aid corner",
        "Emergency sprint",
        "start",
        1,
        "These three beat a better stage. Cut the performance list if you must.",
        "Logistics lead",
        True,
    ),
    EmergencyTemplate(
        "crew",
        "Name shift leads and a stop-the-show person",
        "Emergency sprint",
        "event",
        -1,
        "Every gate and the stage has a name. Volunteers know the end time.",
        "Volunteer lead",
        True,
    ),
    EmergencyTemplate(
        "day",
        "Run entry against the cap",
        "Emergency sprint",
        "event",
        0,
        "Count people in. Pause entry at the cap. Keep water free.",
        "Committee",
        True,
    ),
)


_COMMUNITY_VENDORS = (
    VendorTemplate(
        "permits",
        "Municipal permits and NOC",
        "venue_permits",
        "critical",
        60,
        0,
        (
            "The permission names the footfall cap, the hours, and the site. Your poster "
            "cannot exceed it.",
            "Police intimation and a noise rule are attached before tickets or posts go out.",
        ),
        "Fees belong in this line. A missing permission is a reason to shrink the event, not a "
        "reason to hope.",
    ),
    VendorTemplate(
        "venue",
        "Site or hall",
        "venue_permits",
        "critical",
        45,
        30,
        (
            "Toilets, water points, and power capacity are counted against footfall.",
            "The deposit terms cover cleanup and damage.",
        ),
        "Walk the site at the same time of day as the event.",
    ),
    VendorTemplate(
        "sound",
        "Stage, sound, and power",
        "stage_sound",
        "critical",
        30,
        40,
        (
            "A generator test and fuel are in the quote. Noise ends at the permitted hour.",
            "Cable covers and a rain cover for the board are included outdoors.",
        ),
        "Hire one less performer before you hire a stage you cannot power.",
    ),
    VendorTemplate(
        "safety",
        "Safety, medical, and insurance",
        "safety",
        "critical",
        21,
        30,
        (
            "A first-aid station, a fire point, and public-liability insurance are named.",
            "The contract says who can stop the program.",
        ),
        "Barricades that create a dead end are not a crowd plan.",
    ),
    VendorTemplate(
        "water",
        "Water and refreshments",
        "catering",
        "high",
        21,
        30,
        (
            "Drinking water is free and staffed. Food stalls list allergens and take their "
            "waste back.",
        ),
        "Place water where queues already are, about every 80 metres in an open ground.",
    ),
    VendorTemplate(
        "insurance",
        "Public liability cover",
        "safety",
        "critical",
        21,
        100,
        (
            "The policy period covers setup and breakdown, not only show hours.",
        ),
        "Buy this before the dry run.",
    ),
    VendorTemplate(
        "print",
        "Print and signage",
        "outreach",
        "medium",
        14,
        50,
        (
            "Signs include hours, the water point, the medical point, and the lost-person "
            "point.",
        ),
        "Do not print a footfall claim that the permission does not allow.",
    ),
    VendorTemplate(
        "volunteers",
        "Volunteer leads",
        "volunteers",
        "high",
        30,
        0,
        (
            "Shifts are at most three hours. Leads have a radio or a phone tree and a meal.",
        ),
        "Write the roles down: gate, stage, water, lost-person, waste.",
    ),
)


_COMMUNITY_IDEAS = (
    IdeaTemplate(
        "Staggered entry slots",
        "Give the ground four arrival windows so the gate never holds the full footfall at "
        "once.",
        "{city} sites fail at the gate, not on stage. A cap of {guests} people only works if "
        "they do not arrive together.",
        "medium",
        ("indigo", "chalk", "signal yellow"),
        "A board at the gate that shows the current window and the water point.",
        "Print one site map, not a stack of flyers. Correct it if the cap changes.",
        keywords=("mela", "footfall", "crowd", "ward", "festival"),
        settings=("outdoor", "mixed"),
    ),
    IdeaTemplate(
        "Sponsor the safety line in public",
        "Put sponsor names on the water and medical corner, and publish what their money paid "
        "for.",
        "A community budget in {city} is easier to defend when safety is visibly funded.",
        "low",
        ("teal", "white", "charcoal"),
        "A one-page sponsor note: amount, what it bought, what is still unpaid.",
        "Refuse a sponsor who wants single-use gift junk at the gate.",
        keywords=("sponsor", "grant", "csr", "fund"),
    ),
    IdeaTemplate(
        "Three-hour volunteer shifts",
        "Roster leads, a meal, and a radio channel. End the shift even if the person offers to "
        "stay.",
        "{guests} people need calm marshals. Tired volunteers miss the lost-child call.",
        "medium",
        ("leaf", "sand", "navy"),
        "A briefing card in the language the marshals actually speak.",
        "No new T-shirts if last year's still name the role. Buy water instead.",
        keywords=("volunteer", "ngo", "committee", "neighbourhood"),
    ),
    IdeaTemplate(
        "One stage, local sets",
        "Book a shorter program of local performers and spend the cut on toilets, water, and "
        "shade.",
        "An outdoor program in {city} is a heat and sound problem before it is a lineup "
        "problem.",
        "low",
        ("earth", "white", "temple red"),
        "Shaded seats near the stage reserved for elders and disabled guests, marked in the "
        "map.",
        "End before dark if you do not have budget for a full lighting plot and a safe exit.",
        keywords=("folk", "cultural", "music", "performance"),
        settings=("outdoor",),
    ),
)

def build_community() -> Persona:
    """Civic and community event director. Baseline sums to 1.00."""
    categories = _COMMUNITY_CATEGORIES
    milestones = _COMMUNITY_MILESTONES
    emergency = _COMMUNITY_EMERGENCY
    vendors = _COMMUNITY_VENDORS
    ideas = _COMMUNITY_IDEAS
    return Persona(
        vertical=EventVertical.COMMUNITY,
        name="Community event director",
        summary=(
            "Plans a public gathering around permission, footfall, water, and "
            "a larger contingency. Outreach never outruns the permit."
        ),
        categories=categories,
        contingency_key="contingency",
        contingency_floor=0.10,
        viability_per_guest={
            LocationTier.METRO: 120,
            LocationTier.CITY: 70,
            LocationTier.DESTINATION: 180,
        },
        tier_shifts={
            LocationTier.METRO: {"outreach": -0.02, "safety": 0.02},
        },
        tier_shift_notes={
            LocationTier.METRO: (
                "A metro public event moves 2 points from outreach into safety and crowd "
                "management."
            ),
        },
        age_shifts={},
        age_shift_notes={},
        setting_shifts={
            Setting.OUTDOOR: {"outreach": -0.02, "safety": 0.02},
        },
        setting_shift_notes={
            Setting.OUTDOOR: (
                "An outdoor gathering moves 2 points from outreach into safety for shade, "
                "weather, and crowd flow."
            ),
        },
        milestones=milestones,
        emergency=emergency,
        vendors=vendors,
        ideas=ideas,
        system_brief=(
            "You are planning a community event. Footfall, permission, water, and a way to stop "
            "the show "
            "come before programming. Do not suggest ticket scalping or unpermitted crowds."
        ),
    )
