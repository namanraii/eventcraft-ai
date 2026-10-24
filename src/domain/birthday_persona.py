"""Birthday rule tables.

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
from src.domain.schemas import AgeGroup, EventVertical, LocationTier

_BIRTHDAY_CATEGORIES = (
    CategorySpec(
        "venue_catering",
        "Venue and catering",
        0.32,
        True,
        True,
        "Even a home party has a food cost. This line is the plate, the room, and service.",
    ),
    CategorySpec(
        "entertainment",
        "Entertainment and experiences",
        0.22,
        True,
        False,
        "Birthdays are remembered for one activity, not for matching napkins.",
    ),
    CategorySpec(
        "cake_dessert",
        "Cake and dessert",
        0.12,
        True,
        False,
        "The cake is its own contract: servings, diet, and delivery time.",
    ),
    CategorySpec(
        "decor",
        "Decor and theme",
        0.16,
        False,
        False,
        "Theme spend is capped so it cannot swallow the experience.",
    ),
    CategorySpec(
        "photo_video",
        "Photo and video",
        0.08,
        False,
        False,
        "A few honest hours beat a full-day crew at this scale.",
    ),
    CategorySpec(
        "invites_favors",
        "Invites and favors",
        0.05,
        False,
        False,
        "Paper and gifts are the easiest place to stay small.",
    ),
    CategorySpec(
        "contingency",
        "Buffer",
        0.05,
        True,
        False,
        "A smaller buffer than a wedding, still enough for a delivery miss.",
    ),
)


_BIRTHDAY_MILESTONES = (
    MilestoneTemplate(
        "theme",
        "Lock the theme, the list, and the budget",
        "Theme and guests",
        28,
        "Decide who it is for. A 30th supper and a children's party do not share a vendor "
        "list.",
        "Host",
        True,
    ),
    MilestoneTemplate(
        "early-hold",
        "Hold the room if this is a milestone",
        "Theme and guests",
        90,
        "Used when the date is still far out. A milestone party loses its room to weddings if "
        "you wait.",
        "Host",
        False,
    ),
    MilestoneTemplate(
        "venue",
        "Confirm venue or home setup",
        "Bookings",
        21,
        "Chairs, a cake table, a quiet corner, and a clear end time.",
        "Host",
        True,
    ),
    MilestoneTemplate(
        "experience",
        "Book the one experience",
        "Bookings",
        18,
        "One hired activity is enough. A second activity usually splits the room and the "
        "budget.",
        "Host",
        True,
    ),
    MilestoneTemplate(
        "cake",
        "Brief the cake and the dietary needs",
        "Bookings",
        14,
        "Servings, eggs or eggless, nut policy, and the hour it must be on the table.",
        "Host",
        True,
    ),
    MilestoneTemplate(
        "food",
        "Confirm the menu",
        "Bookings",
        10,
        "Match portions to the list. Children and a seated dinner are different orders.",
        "Host",
        True,
    ),
    MilestoneTemplate(
        "look",
        "Decor, invites, and the playlist",
        "Week of",
        7,
        "Send the address, the end time, and any access note. Keep decor to what you can "
        "store.",
        "Host",
        False,
    ),
    MilestoneTemplate(
        "confirm",
        "Confirm headcount and deliveries",
        "Week of",
        3,
        "Reconfirm the cake delivery window and the experience arrival.",
        "Host",
        True,
    ),
    MilestoneTemplate(
        "eve",
        "Set the room",
        "Day of",
        1,
        "Place seating for anyone who cannot stand, then stop decorating.",
        "Host",
        False,
    ),
    MilestoneTemplate(
        "day",
        "Host the party",
        "Day of",
        0,
        "Start on time and end when you said you would. Neighbours and children both need "
        "that.",
        "Host",
        True,
    ),
)


_BIRTHDAY_EMERGENCY = (
    EmergencyTemplate(
        "list",
        "Freeze the guest list",
        "Emergency sprint",
        "start",
        0,
        "Call the people who matter. Stop expanding the list.",
        "Host",
        True,
    ),
    EmergencyTemplate(
        "place",
        "Pick a home setup or one available room",
        "Emergency sprint",
        "start",
        0,
        "Choose the place you can actually get. A theme can wait.",
        "Host",
        True,
    ),
    EmergencyTemplate(
        "food",
        "Order food and a cake that can be delivered",
        "Emergency sprint",
        "start",
        1,
        "Use a baker who will confirm the diet in writing. Skip a custom sculpture.",
        "Host",
        True,
    ),
    EmergencyTemplate(
        "plan",
        "Write a two-hour running order",
        "Emergency sprint",
        "event",
        -1,
        "Welcome, the one activity or toast, cake, food, goodbye.",
        "Host",
        True,
    ),
    EmergencyTemplate(
        "day",
        "Keep the party inside the hours you announced",
        "Emergency sprint",
        "event",
        0,
        "The buffer is for a late cake, not for a second entertainment booking.",
        "Host",
        True,
    ),
)


_BIRTHDAY_VENDORS = (
    VendorTemplate(
        "venue",
        "Venue or home setup",
        "venue_catering",
        "critical",
        21,
        30,
        (
            "The end time is on the contract. Music and lights stop then.",
            "Damage deposit terms say what counts as damage.",
        ),
        "A home event still needs a rain plan and enough seating.",
    ),
    VendorTemplate(
        "caterer",
        "Caterer",
        "venue_catering",
        "critical",
        14,
        30,
        (
            "Portion counts match the guest list, with a written note for gluten-free or "
            "eggless plates.",
            "Staffing is included, or you have named who will serve.",
        ),
        "Label allergens on the buffet. Do not rely on a verbal warning.",
    ),
    VendorTemplate(
        "cake",
        "Cake maker",
        "cake_dessert",
        "critical",
        10,
        50,
        (
            "Servings, flavour, and the delivery window are the whole order.",
            "A nut-free or eggless requirement is written, not assumed from a phone call.",
        ),
        "Ask what happens if the courier is late. A backup dessert from a nearby shop is a "
        "fair plan.",
    ),
    VendorTemplate(
        "experience",
        "Experience or entertainment",
        "entertainment",
        "high",
        14,
        30,
        (
            "The set length and the age fit are written. A children's set is not a nightclub "
            "set.",
            "Power, space, and a quiet backup if the activity fails are agreed.",
        ),
        "One experience. If the quote doubles the entertainment line, cut the decor instead.",
    ),
    VendorTemplate(
        "decor",
        "Decor",
        "decor",
        "medium",
        10,
        40,
        (
            "Rental items come back the next morning. Balloons and plastic backdrops are a "
            "choice, not a default.",
        ),
        "Decorate one corner the camera will see.",
    ),
    VendorTemplate(
        "photo",
        "Photographer",
        "photo_video",
        "medium",
        14,
        30,
        (
            "Hours and the delivery of a small edited set are dated.",
        ),
        "A friend with a shot list can cover a small dinner if the photo line is tight.",
    ),
    VendorTemplate(
        "invites",
        "Invites",
        "invites_favors",
        "low",
        7,
        0,
        (
            "The message includes the address, end time, and food note.",
        ),
        "A phone message is enough. Print only if someone in the family needs paper.",
    ),
)


_BIRTHDAY_IDEAS = (
    IdeaTemplate(
        "Parallel quiet room",
        "Run a short, loud activity in one space and a quiet making table in another so "
        "children can leave the noise.",
        "A kids' gathering for {guests} people works better with an exit ramp from the "
        "excitement. Host: {host}.",
        "medium",
        ("sunflower", "sky", "paper white"),
        "Twenty-minute sets, then food, then a clear end before bedtime.",
        "Borrow toys and books. Skip a balloon install.",
        keywords=("kid", "kids", "child", "children"),
        age_groups=("kids",),
    ),
    IdeaTemplate(
        "Activity over a spectacle",
        "Give teens one thing to do together — a tournament, a kitchen shift, a playlist they "
        "built — and almost no stage decor.",
        "{event_name} lands better when the guests own part of it. {city} has plenty of rooms; "
        "the activity is the scarce piece.",
        "medium",
        ("ink", "electric blue", "concrete"),
        "A shared playlist with a volume cap and a last song.",
        "Digital invites only. No favor that will be binned on the way home.",
        age_groups=("teens",),
    ),
    IdeaTemplate(
        "Supper club, one toast",
        "A seated meal, a family toast before service, and a playlist after. No ceremony "
        "unless the notes ask for one.",
        "This fits a milestone dinner in {city} for {guests} guests, with gluten-free plates "
        "marked before anyone sits.",
        "medium",
        ("oxblood", "cream", "brass"),
        "One speech, three minutes, then the meal.",
        "Choose a restaurant or caterer that already cooks to order so you do not build a new "
        "kitchen.",
        keywords=("supper", "dinner", "toast", "retro"),
        age_groups=("milestone_21", "milestone_30", "general"),
    ),
    IdeaTemplate(
        "Memory table, earlier end",
        "A table of photos and stories, seats with backs for everyone, and an end time that "
        "lets people travel home.",
        "A 50th in {city} is a gathering of energy levels. Comfort spends better than a late "
        "band.",
        "low",
        ("sage", "warm grey", "gold line"),
        "Short open-mic stories with a host who will gently stop them.",
        "Print a small photo run instead of a new decor hire.",
        age_groups=("milestone_50",),
        keywords=("50", "jubilee", "elder"),
    ),
    IdeaTemplate(
        "Home courtyard hour",
        "Use the house, hire the meal, and put the money into the cake and one musician or a "
        "game.",
        "{guests} guests can fit a home plan when the venue line would otherwise erase the "
        "experience.",
        "low",
        ("terracotta", "white", "green"),
        "Cake at a stated time, then tea.",
        "Reusable plates. The buffer covers breakage, not a second theme.",
        settings=("indoor", "mixed"),
    ),
)

def build_birthday() -> Persona:
    """Milestone birthday curator. Baseline sums to 1.00."""
    categories = _BIRTHDAY_CATEGORIES
    milestones = _BIRTHDAY_MILESTONES
    emergency = _BIRTHDAY_EMERGENCY
    vendors = _BIRTHDAY_VENDORS
    ideas = _BIRTHDAY_IDEAS
    return Persona(
        vertical=EventVertical.BIRTHDAY,
        name="Birthday curator",
        summary=(
            "Plans a birthday as a short sprint: one experience, a real cake contract, "
            "and a four-week path that compresses cleanly if the date is sooner."
        ),
        categories=categories,
        contingency_key="contingency",
        contingency_floor=0.04,
        viability_per_guest={
            LocationTier.METRO: 700,
            LocationTier.CITY: 450,
            LocationTier.DESTINATION: 1_100,
        },
        tier_shifts={
            LocationTier.DESTINATION: {"invites_favors": -0.02, "venue_catering": 0.02},
        },
        tier_shift_notes={
            LocationTier.DESTINATION: (
                "A destination birthday moves 2 points from invites and favors into the room and "
                "the meal."
            ),
        },
        age_shifts={
            AgeGroup.KIDS: {
                "entertainment": 0.04,
                "cake_dessert": 0.02,
                "photo_video": -0.03,
                "invites_favors": -0.03,
            },
            AgeGroup.TEENS: {"entertainment": 0.05, "decor": -0.03, "photo_video": -0.02},
            AgeGroup.MILESTONE_50: {"venue_catering": 0.04, "entertainment": -0.04},
        },
        age_shift_notes={
            AgeGroup.KIDS: "A children's party moves weight into the activity and the cake, and "
                "away from photo and favors.",
            AgeGroup.TEENS: "A teen party funds the activity and trims decor and photo.",
            AgeGroup.MILESTONE_50: "A 50th moves weight from entertainment into seating, food, and "
                "a calmer room.",
        },
        setting_shifts={},
        setting_shift_notes={},
        milestones=milestones,
        emergency=emergency,
        vendors=vendors,
        ideas=ideas,
        system_brief=(
            "You are planning a birthday. Match the age. One signature experience is better than a "
            "theme park of ideas. "
            "Do not add alcohol service unless the notes ask for it."
        ),
    )
