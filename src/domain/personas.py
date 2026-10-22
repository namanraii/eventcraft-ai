"""Strategy data for the three celebration personas.

Weights, lead times, and idea libraries live here so the engines stay
mechanical: they apply these rules to a date and a budget. Wedding is the
flagship persona. Birthday and community events use the same engine code
with different rules.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.schemas import AgeGroup, EventVertical, LocationTier, Setting


@dataclass(frozen=True)
class CategorySpec:
    """A budget line and the reason it exists for this persona."""

    key: str
    label: str
    base_weight: float
    critical: bool
    per_guest: bool
    rationale: str


@dataclass(frozen=True)
class MilestoneTemplate:
    """A phased task measured in days before the main event date."""

    id: str
    title: str
    phase: str
    days_before_event: int
    description: str
    owner: str
    critical: bool


@dataclass(frozen=True)
class EmergencyTemplate:
    """A task used only when fewer than 14 days remain.

    ``anchor`` is ``start`` (today) or ``event`` (the event date).
    ``offset_days`` is added to that anchor. Negative offsets land before it.
    """

    id: str
    title: str
    phase: str
    anchor: str
    offset_days: int
    description: str
    owner: str
    critical: bool


@dataclass(frozen=True)
class VendorTemplate:
    """A checklist row. Keyword rows appear only when the brief mentions them."""

    id: str
    vendor_role: str
    category_key: str
    priority: str
    lead_time_days: int
    deposit_percent: int
    contract_clauses: tuple[str, ...]
    notes: str
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdeaTemplate:
    """A reusable concept. Placeholders: {city}, {guests}, {host}, {event_name}."""

    title: str
    summary: str
    why_it_fits: str
    effort: str
    palette: tuple[str, ...]
    signature_experience: str
    sustainability_tip: str
    keywords: tuple[str, ...] = ()
    age_groups: tuple[str, ...] = ()
    settings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Persona:
    """The full rule set for one vertical."""

    vertical: EventVertical
    name: str
    summary: str
    categories: tuple[CategorySpec, ...]
    contingency_key: str
    contingency_floor: float
    viability_per_guest: dict[LocationTier, int]
    tier_shifts: dict[LocationTier, dict[str, float]]
    tier_shift_notes: dict[LocationTier, str]
    age_shifts: dict[AgeGroup, dict[str, float]]
    age_shift_notes: dict[AgeGroup, str]
    setting_shifts: dict[Setting, dict[str, float]]
    setting_shift_notes: dict[Setting, str]
    milestones: tuple[MilestoneTemplate, ...]
    emergency: tuple[EmergencyTemplate, ...]
    vendors: tuple[VendorTemplate, ...]
    ideas: tuple[IdeaTemplate, ...]
    system_brief: str

    def category(self, key: str) -> CategorySpec:
        """Return one category specification by key."""
        for item in self.categories:
            if item.key == key:
                return item
        raise KeyError(key)


def _wedding() -> Persona:
    """Royal and modern wedding architect. Baseline sums to 1.00."""
    categories = (
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
    milestones = (
        MilestoneTemplate(
            "vision",
            "Write the brief and the guest ceiling",
            "Concept and venue",
            300,
            "Agree the rituals you will actually do, a guest ceiling, and the budget you will not cross.",
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
            "Lock ceremony hours first. Add pre-events only if the quote still fits the photo line.",
            "Couple",
            True,
        ),
        MilestoneTemplate(
            "catering",
            "Tasting and caterer contract",
            "Vendors and contracts",
            160,
            "Taste the menu, separate allergen and Jain lines if needed, and freeze the per-plate rule.",
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
            "Include a map, the meal type, and a realistic RSVP date. Digital is fine if elders have a phone path.",
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
            "Walk the procession, the meal service, and the exit. Name one person who can make a decision on the day.",
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
            "Run the day from the one-page sheet. The buffer exists so you do not renegotiate prices at the gate.",
            "Couple",
            True,
        ),
    )
    emergency = (
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
            "One venue, home, or courtyard. Get the overtime rate and the backup power in writing today.",
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
            "Hire photo for the ceremony window. Skip a full-day film crew if the date is this close.",
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
    vendors = (
        VendorTemplate(
            "venue",
            "Venue",
            "venue_catering",
            "critical",
            180,
            40,
            (
                "Cancellation keeps a dated schedule: a shift to a new date is better than a forfeiture inside 30 days.",
                "Overtime has an hourly cap written on the work order, including music curfew.",
                "Power backup, drinking water, and a rain cover are included or priced as line items.",
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
                "The final bill uses the higher of the guaranteed count and the plates served, locked 72 hours prior.",
                "Allergen and special-diet counters have their own serving staff so lines do not cross.",
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
                "Delivery days for edited films and for the full set of photos are dates, not 'soon'.",
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
                "The drawing is the scope. Extra florals on the day are a new quote, not a surprise line.",
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
                "Alteration deadlines are on the receipt. A missed fitting is not the tailor's overtime gift.",
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
                "The room block release date is before your RSVP close, with a named attrition percentage.",
                "Airport or station transfers list the vehicle count, not an open-ended 'as required'.",
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
                "Sound ends at the venue curfew. Overtime is a pre-priced hour, not a negotiation at midnight.",
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
                "The ritual duration is an estimate in minutes so the venue overtime is predictable.",
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
                "The proof you signed is the print. Spelling corrections after print are a new job.",
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
                "The artist count matches the number of guests you want finished before the ceremony, not a vague team.",
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
    ideas = (
        IdeaTemplate(
            "Courtyard ceremony, short baraat",
            "Hold the rites in one courtyard and keep the procession to a few hundred metres so transport does not eat the hospitality line.",
            "{city} can carry a courtyard wedding for {guests} guests without a second venue. {host} stay with the guests instead of spending the hour in traffic.",
            "medium",
            ("sandstone", "marigold", "ivory"),
            "A shehnai or nadaswaram at the gate, then silence for the vows.",
            "Skip a foam-flower hall. Use one seasonal garland on the mandap and family textiles for the rest.",
            keywords=("rajasthani", "courtyard", "baraat", "shehnai", "jaipur"),
            settings=("outdoor", "mixed"),
        ),
        IdeaTemplate(
            "Two kitchen lines, one dining hall",
            "Run the main vegetarian meal and a separate Jain or allergen line with different ladles, boards, and staff.",
            "The dietary note is specific, and {guests} guests is large enough that a shared spoon will fail.",
            "medium",
            ("banana leaf", "brass", "white"),
            "A millet or regional thali that elders recognise, plus a smaller plate for children.",
            "Plan portions from RSVPs, not from a 10 percent over-guess. Donate sealed surplus the same night.",
            keywords=("jain", "vegetarian", "vegan", "allergen", "onion"),
        ),
        IdeaTemplate(
            "Heirloom textile mandap",
            "Build the canopy from family sarees and one florist focal, and spend the decor cut on guest comfort instead.",
            "You marked decor as a lower priority. A textile mandap still photographs as a wedding in {city}.",
            "low",
            ("indigo", "madder", "unbleached cotton"),
            "Each corner held by a textile with a one-line story in the program.",
            "Rent the structure and return it. Buy almost no single-use florals.",
            keywords=("decor", "textile", "saree", "minimal"),
        ),
        IdeaTemplate(
            "Daylight rites, seated lunch",
            "Start late morning, finish the meal before evening traffic, and skip a night party if the families are tired of them.",
            "A daytime plan in {city} keeps overtime and generator fuel off the invoice for {guests} guests.",
            "low",
            ("warm white", "leaf green", "clay"),
            "A family playlist for one hour after lunch, then a clear end.",
            "Daylight cuts lighting hire and lets elders travel home before dark.",
            keywords=("lunch", "daytime", "elder", "morning"),
        ),
    )
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


def _birthday() -> Persona:
    """Milestone birthday curator. Baseline sums to 1.00."""
    categories = (
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
    milestones = (
        MilestoneTemplate(
            "theme",
            "Lock the theme, the list, and the budget",
            "Theme and guests",
            28,
            "Decide who it is for. A 30th supper and a children's party do not share a vendor list.",
            "Host",
            True,
        ),
        MilestoneTemplate(
            "early-hold",
            "Hold the room if this is a milestone",
            "Theme and guests",
            90,
            "Used when the date is still far out. A milestone party loses its room to weddings if you wait.",
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
            "One hired activity is enough. A second activity usually splits the room and the budget.",
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
            "Send the address, the end time, and any access note. Keep decor to what you can store.",
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
            "Start on time and end when you said you would. Neighbours and children both need that.",
            "Host",
            True,
        ),
    )
    emergency = (
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
    vendors = (
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
                "Portion counts match the guest list, with a written note for gluten-free or eggless plates.",
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
            "Ask what happens if the courier is late. A backup dessert from a nearby shop is a fair plan.",
        ),
        VendorTemplate(
            "experience",
            "Experience or entertainment",
            "entertainment",
            "high",
            14,
            30,
            (
                "The set length and the age fit are written. A children's set is not a nightclub set.",
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
                "Rental items come back the next morning. Balloons and plastic backdrops are a choice, not a default.",
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
    ideas = (
        IdeaTemplate(
            "Parallel quiet room",
            "Run a short, loud activity in one space and a quiet making table in another so children can leave the noise.",
            "A kids' gathering for {guests} people works better with an exit ramp from the excitement. Host: {host}.",
            "medium",
            ("sunflower", "sky", "paper white"),
            "Twenty-minute sets, then food, then a clear end before bedtime.",
            "Borrow toys and books. Skip a balloon install.",
            keywords=("kid", "kids", "child", "children"),
            age_groups=("kids",),
        ),
        IdeaTemplate(
            "Activity over a spectacle",
            "Give teens one thing to do together — a tournament, a kitchen shift, a playlist they built — and almost no stage decor.",
            "{event_name} lands better when the guests own part of it. {city} has plenty of rooms; the activity is the scarce piece.",
            "medium",
            ("ink", "electric blue", "concrete"),
            "A shared playlist with a volume cap and a last song.",
            "Digital invites only. No favor that will be binned on the way home.",
            age_groups=("teens",),
        ),
        IdeaTemplate(
            "Supper club, one toast",
            "A seated meal, a family toast before service, and a playlist after. No ceremony unless the notes ask for one.",
            "This fits a milestone dinner in {city} for {guests} guests, with gluten-free plates marked before anyone sits.",
            "medium",
            ("oxblood", "cream", "brass"),
            "One speech, three minutes, then the meal.",
            "Choose a restaurant or caterer that already cooks to order so you do not build a new kitchen.",
            keywords=("supper", "dinner", "toast", "retro"),
            age_groups=("milestone_21", "milestone_30", "general"),
        ),
        IdeaTemplate(
            "Memory table, earlier end",
            "A table of photos and stories, seats with backs for everyone, and an end time that lets people travel home.",
            "A 50th in {city} is a gathering of energy levels. Comfort spends better than a late band.",
            "low",
            ("sage", "warm grey", "gold line"),
            "Short open-mic stories with a host who will gently stop them.",
            "Print a small photo run instead of a new decor hire.",
            age_groups=("milestone_50",),
            keywords=("50", "jubilee", "elder"),
        ),
        IdeaTemplate(
            "Home courtyard hour",
            "Use the house, hire the meal, and put the money into the cake and one musician or a game.",
            "{guests} guests can fit a home plan when the venue line would otherwise erase the experience.",
            "low",
            ("terracotta", "white", "green"),
            "Cake at a stated time, then tea.",
            "Reusable plates. The buffer covers breakage, not a second theme.",
            settings=("indoor", "mixed"),
        ),
    )
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
                "A destination birthday moves 2 points from invites and favors into the room and the meal."
            ),
        },
        age_shifts={
            AgeGroup.KIDS: {"entertainment": 0.04, "cake_dessert": 0.02, "photo_video": -0.03, "invites_favors": -0.03},
            AgeGroup.TEENS: {"entertainment": 0.05, "decor": -0.03, "photo_video": -0.02},
            AgeGroup.MILESTONE_50: {"venue_catering": 0.04, "entertainment": -0.04},
        },
        age_shift_notes={
            AgeGroup.KIDS: "A children's party moves weight into the activity and the cake, and away from photo and favors.",
            AgeGroup.TEENS: "A teen party funds the activity and trims decor and photo.",
            AgeGroup.MILESTONE_50: "A 50th moves weight from entertainment into seating, food, and a calmer room.",
        },
        setting_shifts={},
        setting_shift_notes={},
        milestones=milestones,
        emergency=emergency,
        vendors=vendors,
        ideas=ideas,
        system_brief=(
            "You are planning a birthday. Match the age. One signature experience is better than a theme park of ideas. "
            "Do not add alcohol service unless the notes ask for it."
        ),
    )


def _community() -> Persona:
    """Civic and community event director. Baseline sums to 1.00."""
    categories = (
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
            "Municipal events overrun on power, water, and last-minute compliance. The reserve is larger on purpose.",
        ),
    )
    milestones = (
        MilestoneTemplate(
            "brief",
            "Fix footfall, budget, and the sponsor gap",
            "Permissions and site",
            90,
            "Write the maximum footfall you will allow. Sponsorship reduces the gap; it does not raise the cap.",
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
            "Barricades, a fire extinguisher point, a first-aid corner, and a written weather call.",
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
            "Publish hours, the gate plan, and what is free. Correct the footfall if permission came back lower.",
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
    emergency = (
        EmergencyTemplate(
            "legal",
            "Check whether the gathering is still lawful",
            "Emergency sprint",
            "start",
            0,
            "If a permit or NOC is required and not filed, reduce footfall to a private meeting or move the date. Do not advertise a crowd you cannot host.",
            "Committee",
            True,
        ),
        EmergencyTemplate(
            "cap",
            "Publish a hard footfall cap",
            "Emergency sprint",
            "start",
            0,
            "Pick a number the site can hold with water and a medical corner. Staff the gate to that number.",
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
    vendors = (
        VendorTemplate(
            "permits",
            "Municipal permits and NOC",
            "venue_permits",
            "critical",
            60,
            0,
            (
                "The permission names the footfall cap, the hours, and the site. Your poster cannot exceed it.",
                "Police intimation and a noise rule are attached before tickets or posts go out.",
            ),
            "Fees belong in this line. A missing permission is a reason to shrink the event, not a reason to hope.",
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
                "Drinking water is free and staffed. Food stalls list allergens and take their waste back.",
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
                "Signs include hours, the water point, the medical point, and the lost-person point.",
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
    ideas = (
        IdeaTemplate(
            "Staggered entry slots",
            "Give the ground four arrival windows so the gate never holds the full footfall at once.",
            "{city} sites fail at the gate, not on stage. A cap of {guests} people only works if they do not arrive together.",
            "medium",
            ("indigo", "chalk", "signal yellow"),
            "A board at the gate that shows the current window and the water point.",
            "Print one site map, not a stack of flyers. Correct it if the cap changes.",
            keywords=("mela", "footfall", "crowd", "ward", "festival"),
            settings=("outdoor", "mixed"),
        ),
        IdeaTemplate(
            "Sponsor the safety line in public",
            "Put sponsor names on the water and medical corner, and publish what their money paid for.",
            "A community budget in {city} is easier to defend when safety is visibly funded.",
            "low",
            ("teal", "white", "charcoal"),
            "A one-page sponsor note: amount, what it bought, what is still unpaid.",
            "Refuse a sponsor who wants single-use gift junk at the gate.",
            keywords=("sponsor", "grant", "csr", "fund"),
        ),
        IdeaTemplate(
            "Three-hour volunteer shifts",
            "Roster leads, a meal, and a radio channel. End the shift even if the person offers to stay.",
            "{guests} people need calm marshals. Tired volunteers miss the lost-child call.",
            "medium",
            ("leaf", "sand", "navy"),
            "A briefing card in the language the marshals actually speak.",
            "No new T-shirts if last year's still name the role. Buy water instead.",
            keywords=("volunteer", "ngo", "committee", "neighbourhood"),
        ),
        IdeaTemplate(
            "One stage, local sets",
            "Book a shorter program of local performers and spend the cut on toilets, water, and shade.",
            "An outdoor program in {city} is a heat and sound problem before it is a lineup problem.",
            "low",
            ("earth", "white", "temple red"),
            "Shaded seats near the stage reserved for elders and disabled guests, marked in the map.",
            "End before dark if you do not have budget for a full lighting plot and a safe exit.",
            keywords=("folk", "cultural", "music", "performance"),
            settings=("outdoor",),
        ),
    )
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
                "A metro public event moves 2 points from outreach into safety and crowd management."
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
            "You are planning a community event. Footfall, permission, water, and a way to stop the show "
            "come before programming. Do not suggest ticket scalping or unpermitted crowds."
        ),
    )


PERSONAS: dict[EventVertical, Persona] = {
    EventVertical.WEDDING: _wedding(),
    EventVertical.BIRTHDAY: _birthday(),
    EventVertical.COMMUNITY: _community(),
}


def get_persona(vertical: EventVertical) -> Persona:
    """Return the rule set for a vertical.

    Args:
        vertical: One of the three challenge personas.

    Returns:
        The matching persona. The dictionary covers every enum value.
    """
    return PERSONAS[vertical]


def public_catalog() -> list[dict[str, object]]:
    """Return persona metadata the form uses to draw priority sliders.

    Weights are exposed as percents. The server remains the source of truth
    when it allocates money; the UI does not recompute the split.
    """
    catalog: list[dict[str, object]] = []
    for persona in PERSONAS.values():
        catalog.append(
            {
                "event_type": persona.vertical.value,
                "name": persona.name,
                "summary": persona.summary,
                "flagship": persona.vertical is EventVertical.WEDDING,
                "categories": [
                    {
                        "key": category.key,
                        "label": category.label,
                        "base_percent": round(category.base_weight * 100, 1),
                        "critical": category.critical,
                        "adjustable": category.key != persona.contingency_key,
                    }
                    for category in persona.categories
                ],
            }
        )
    return catalog
