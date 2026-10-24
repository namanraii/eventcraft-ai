"""Wedding rule tables.

The flagship persona. The builder only assembles these tables."""

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

_WEDDING_CATEGORIES = (
    CategorySpec(
        "venue_catering",
        "Venue and catering",
        0.45,
        True,
        True,
        "The room and the meal decide whether the day feels hosted.",
    ),
    CategorySpec(
        "decor",
        "Decor and florals",
        0.15,
        False,
        False,
        "Decor is the first place to simplify when the guest list grows.",
    ),
    CategorySpec(
        "photo_video",
        "Photo and video",
        0.12,
        False,
        False,
        "Coverage is booked early because good teams hold dates.",
    ),
    CategorySpec(
        "attire_hospitality",
        "Attire and guest hospitality",
        0.10,
        False,
        False,
        "Clothes, rooms, and transfers sit together because families feel both.",
    ),
    CategorySpec(
        "entertainment",
        "Entertainment and rituals",
        0.08,
        False,
        False,
        "Music and ritual teams need a cue sheet, not only a playlist.",
    ),
    CategorySpec(
        "contingency",
        "Emergency buffer",
        0.10,
        True,
        False,
        "Ten percent stays unspent so a late headcount does not break the meal.",
    ),
)


_WEDDING_MILESTONES = (
    MilestoneTemplate(
        "vision",
        "Write the brief and the guest ceiling",
        "Concept and venue",
        300,
        "Agree the rituals you will actually do, a guest ceiling, and the budget you will not "
        "cross.",
        "Couple and families",
        True,
    ),
    MilestoneTemplate(
        "venue",
        "Hold the venue with a written date",
        "Concept and venue",
        240,
        "Confirm load-in hours, a rain plan, overtime rates, and who provides power backup.",
        "Couple",
        True,
    ),
    MilestoneTemplate(
        "photo",
        "Book photo and video",
        "Vendors and contracts",
        200,
        "Lock ceremony hours first. Add pre-events only if the quote still fits the photo "
        "line.",
        "Couple",
        True,
    ),
    MilestoneTemplate(
        "catering",
        "Tasting and caterer contract",
        "Vendors and contracts",
        160,
        "Taste the menu, separate allergen and Jain lines if needed, and freeze the per-plate "
        "rule.",
        "Couple",
        True,
    ),
    MilestoneTemplate(
        "decor",
        "Decor, florals, and mandap or stage",
        "Vendors and contracts",
        140,
        "Approve a drawing with dimensions. Ban open flame where the venue forbids it.",
        "Couple",
        False,
    ),
    MilestoneTemplate(
        "attire",
        "Attire fittings and room block",
        "Vendors and contracts",
        110,
        "Book alteration time and a hospitality block for elders before peak dates disappear.",
        "Families",
        False,
    ),
    MilestoneTemplate(
        "invites",
        "Send invitations",
        "Guest logistics",
        80,
        "Include a map, the meal type, and a realistic RSVP date. Digital is fine if elders "
        "have a phone path.",
        "Families",
        False,
    ),
    MilestoneTemplate(
        "rituals",
        "Confirm ritual and music teams",
        "Guest logistics",
        50,
        "Share the order of ceremonies, the sound curfew, and who cues the processions.",
        "Couple",
        True,
    ),
    MilestoneTemplate(
        "rsvp",
        "Close RSVPs and lock hospitality",
        "Guest logistics",
        30,
        "Turn the guest list into a headcount, a rooming list, and a transport list.",
        "Families",
        True,
    ),
    MilestoneTemplate(
        "final-pay",
        "Final headcount and vendor payments",
        "Run of show",
        14,
        "Pay what the contracts say is due. Send one run-of-show to every vendor.",
        "Couple",
        True,
    ),
    MilestoneTemplate(
        "rehearsal",
        "Rehearse the cue sheet",
        "Run of show",
        7,
        "Walk the procession, the meal service, and the exit. Name one person who can make a "
        "decision on the day.",
        "Couple",
        True,
    ),
    MilestoneTemplate(
        "eve",
        "Day-before confirmation calls",
        "Run of show",
        1,
        "Confirm arrival times, the meal count, and a wet-weather swap if you are outdoors.",
        "Couple",
        True,
    ),
    MilestoneTemplate(
        "day",
        "Ceremony day cue sheet",
        "Run of show",
        0,
        "Run the day from the one-page sheet. The buffer exists so you do not renegotiate "
        "prices at the gate.",
        "Couple",
        True,
    ),
)


_WEDDING_EMERGENCY = (
    EmergencyTemplate(
        "freeze",
        "Freeze the guest list and the rituals",
        "Emergency sprint",
        "start",
        0,
        "Write the three rituals you will keep. Everything else waits.",
        "Couple",
        True,
    ),
    EmergencyTemplate(
        "place",
        "Confirm the room, power, and a rain cover",
        "Emergency sprint",
        "start",
        0,
        "One venue, home, or courtyard. Get the overtime rate and the backup power in writing "
        "today.",
        "Couple",
        True,
    ),
    EmergencyTemplate(
        "food",
        "Lock food and a simple decor package",
        "Emergency sprint",
        "start",
        1,
        "Prefer one vendor for food and a restrained decor kit. Ask what they can still staff.",
        "Couple",
        True,
    ),
    EmergencyTemplate(
        "photo-rush",
        "Book ceremony-hour coverage only",
        "Emergency sprint",
        "start",
        1,
        "Hire photo for the ceremony window. Skip a full-day film crew if the date is this "
        "close.",
        "Couple",
        False,
    ),
    EmergencyTemplate(
        "sheet",
        "Send a one-page run of show",
        "Emergency sprint",
        "event",
        -1,
        "Arrival, ceremony, meal, exit. One phone number for decisions.",
        "Couple",
        True,
    ),
    EmergencyTemplate(
        "day",
        "Host the day from the cue sheet",
        "Emergency sprint",
        "event",
        0,
        "Do not add vendors on the morning. Use the buffer for a real overrun only.",
        "Couple",
        True,
    ),
)


_WEDDING_VENDORS = (
    VendorTemplate(
        "venue",
        "Venue",
        "venue_catering",
        "critical",
        180,
        40,
        (
            "Cancellation keeps a dated schedule: a shift to a new date is better than a "
            "forfeiture inside 30 days.",
            "Overtime has an hourly cap written on the work order, including music curfew.",
            "Power backup, drinking water, and a rain cover are included or priced as line "
            "items.",
        ),
        "Visit once at the same hour as the ceremony so you hear the real ambient noise.",
    ),
    VendorTemplate(
        "caterer",
        "Caterer",
        "venue_catering",
        "critical",
        120,
        30,
        (
            "The final bill uses the higher of the guaranteed count and the plates served, "
            "locked 72 hours prior.",
            "Allergen and special-diet counters have their own serving staff so lines do not "
            "cross.",
            "Leftover packing is allowed for the family, or the contract says it is not.",
        ),
        "Pay for a tasting. A menu you have not eaten is a guess.",
    ),
    VendorTemplate(
        "photo",
        "Photographer and films",
        "photo_video",
        "critical",
        150,
        30,
        (
            "Delivery days for edited films and for the full set of photos are dates, not "
            "'soon'.",
            "A second shooter is included only for the hours you listed.",
            "You can print and share guest photos. The vendor keeps portfolio rights.",
        ),
        "Ask who actually stands at the ceremony if the studio sends an associate.",
    ),
    VendorTemplate(
        "decor",
        "Decor and florals",
        "decor",
        "high",
        90,
        40,
        (
            "The drawing is the scope. Extra florals on the day are a new quote, not a "
            "surprise line.",
            "Installation and breakdown hours are inside the venue's access window.",
            "Open flame, cold pyro, and hanging loads need the venue's written yes.",
        ),
        "Fresh flowers for one focal point beat a hall of foam arrangements.",
    ),
    VendorTemplate(
        "attire",
        "Attire and styling",
        "attire_hospitality",
        "high",
        90,
        50,
        (
            "Alteration deadlines are on the receipt. A missed fitting is not the tailor's "
            "overtime gift.",
            "Duplicate jewellery or a backup outfit is named if the main piece is borrowed.",
        ),
        "Schedule the last fitting at least four days before travel.",
    ),
    VendorTemplate(
        "rooms",
        "Guest rooms and transfers",
        "attire_hospitality",
        "high",
        90,
        30,
        (
            "The room block release date is before your RSVP close, with a named attrition "
            "percentage.",
            "Airport or station transfers list the vehicle count, not an open-ended 'as "
            "required'.",
        ),
        "Hold rooms for elders first. Everyone else can book the published rate.",
    ),
    VendorTemplate(
        "music",
        "Music and hosts",
        "entertainment",
        "medium",
        60,
        30,
        (
            "Sound ends at the venue curfew. Overtime is a pre-priced hour, not a negotiation "
            "at midnight.",
            "The repertoire for rituals is approved. The dance set is a separate block.",
        ),
        "One emcee who has read the family names is worth more than a louder speaker.",
    ),
    VendorTemplate(
        "officiant",
        "Officiant or ritual lead",
        "entertainment",
        "critical",
        60,
        20,
        (
            "The ritual duration is an estimate in minutes so the venue overtime is "
            "predictable.",
            "Language and the order of rites are agreed in writing.",
        ),
        "Ask what the family must arrange: fire pit, mandap access, or a quiet side room.",
    ),
    VendorTemplate(
        "invites",
        "Invitations",
        "attire_hospitality",
        "medium",
        45,
        50,
        (
            "The proof you signed is the print. Spelling corrections after print are a new "
            "job.",
        ),
        "Put the meal type and the RSVP date on the card itself.",
    ),
    VendorTemplate(
        "mehendi",
        "Mehendi artist",
        "entertainment",
        "medium",
        45,
        30,
        (
            "The artist count matches the number of guests you want finished before the "
            "ceremony, not a vague team.",
            "Stain-darkening time is scheduled before portraits.",
        ),
        "Included because the brief mentions mehendi.",
        keywords=("mehendi", "mehndi"),
    ),
    VendorTemplate(
        "sangeet",
        "Sangeet production",
        "entertainment",
        "medium",
        45,
        40,
        (
            "Rehearsal hours, the choreographer, and the sound check are separate line items.",
        ),
        "Included because the brief mentions a sangeet.",
        keywords=("sangeet",),
    ),
)


_WEDDING_IDEAS = (
    IdeaTemplate(
        "Courtyard ceremony, short baraat",
        "Hold the rites in one courtyard and keep the procession to a few hundred metres so "
        "transport does not eat the hospitality line.",
        "{city} can carry a courtyard wedding for {guests} guests without a second venue. "
        "{host} stay with the guests instead of spending the hour in traffic.",
        "medium",
        ("sandstone", "marigold", "ivory"),
        "A shehnai or nadaswaram at the gate, then silence for the vows.",
        "Skip a foam-flower hall. Use one seasonal garland on the mandap and family textiles "
        "for the rest.",
        keywords=("rajasthani", "courtyard", "baraat", "shehnai", "jaipur"),
        settings=("outdoor", "mixed"),
    ),
    IdeaTemplate(
        "Two kitchen lines, one dining hall",
        "Run the main vegetarian meal and a separate Jain or allergen line with different "
        "ladles, boards, and staff.",
        "The dietary note is specific, and {guests} guests is large enough that a shared spoon "
        "will fail.",
        "medium",
        ("banana leaf", "brass", "white"),
        "A millet or regional thali that elders recognise, plus a smaller plate for children.",
        "Plan portions from RSVPs, not from a 10 percent over-guess. Donate sealed surplus the "
        "same night.",
        keywords=("jain", "vegetarian", "vegan", "allergen", "onion"),
    ),
    IdeaTemplate(
        "Heirloom textile mandap",
        "Build the canopy from family sarees and one florist focal, and spend the decor cut on "
        "guest comfort instead.",
        "You marked decor as a lower priority. A textile mandap still photographs as a wedding "
        "in {city}.",
        "low",
        ("indigo", "madder", "unbleached cotton"),
        "Each corner held by a textile with a one-line story in the program.",
        "Rent the structure and return it. Buy almost no single-use florals.",
        keywords=("decor", "textile", "saree", "minimal"),
    ),
    IdeaTemplate(
        "Daylight rites, seated lunch",
        "Start late morning, finish the meal before evening traffic, and skip a night party if "
        "the families are tired of them.",
        "A daytime plan in {city} keeps overtime and generator fuel off the invoice for "
        "{guests} guests.",
        "low",
        ("warm white", "leaf green", "clay"),
        "A family playlist for one hour after lunch, then a clear end.",
        "Daylight cuts lighting hire and lets elders travel home before dark.",
        keywords=("lunch", "daytime", "elder", "morning"),
    ),
)

def build_wedding() -> Persona:
    """Royal and modern wedding architect. Baseline sums to 1.00."""
    categories = _WEDDING_CATEGORIES
    milestones = _WEDDING_MILESTONES
    emergency = _WEDDING_EMERGENCY
    vendors = _WEDDING_VENDORS
    ideas = _WEDDING_IDEAS
    return Persona(
        vertical=EventVertical.WEDDING,
        name="Wedding architect",
        summary=(
            "Plans a multi-ritual wedding backward from the ceremony date, "
            "with venue and food as the protected spend and a 10 percent buffer."
        ),
        categories=categories,
        contingency_key="contingency",
        contingency_floor=0.08,
        viability_per_guest={
            LocationTier.METRO: 1_500,
            LocationTier.CITY: 900,
            LocationTier.DESTINATION: 2_200,
        },
        tier_shifts={
            LocationTier.DESTINATION: {"decor": -0.03, "attire_hospitality": 0.03},
        },
        tier_shift_notes={
            LocationTier.DESTINATION: (
                "Destination tier moves 3 points from decor into attire and hospitality "
                "for rooms and transfers."
            ),
        },
        age_shifts={},
        age_shift_notes={},
        setting_shifts={
            Setting.OUTDOOR: {"decor": -0.02, "venue_catering": 0.02},
        },
        setting_shift_notes={
            Setting.OUTDOOR: (
                "An outdoor ceremony moves 2 points from decor into venue and catering "
                "for cover, power, and water."
            ),
        },
        milestones=milestones,
        emergency=emergency,
        vendors=vendors,
        ideas=ideas,
        system_brief=(
            "You are planning a wedding. Protect the meal, the rite, and a way home for elders. "
            "Do not invent a religion the notes do not state."
        ),
    )
