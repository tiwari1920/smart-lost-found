"""Metadata similarity: compares the STRUCTURED fields of a lost and a found item.

Every function returns a score from 0.0 (nothing in common) to 1.0 (identical).
These rules are PROJECT-DEFINED. They are simple, explainable rules,
not scientifically validated probabilities.
"""
import re
from datetime import datetime


# ----------------------------------------------------------------------
# Cleaning helpers
# ----------------------------------------------------------------------
def normalize_text(value):
    """'  Dark-Blue!! ' -> 'dark blue' (lowercase, no punctuation, single spaces)."""
    if not value:
        return ''
    value = re.sub(r'[^a-z0-9\s]', ' ', value.lower())  # punctuation -> space
    return ' '.join(value.split())                      # remove extra spaces


# ----------------------------------------------------------------------
# A. Category: same = 1.0, different = 0.0
# ----------------------------------------------------------------------
def category_similarity(category_a, category_b):
    a = (category_a or '').strip().upper()
    b = (category_b or '').strip().upper()
    return 1.0 if a and a == b else 0.0


# ----------------------------------------------------------------------
# B. Colour: compare SETS of colour words (Jaccard similarity)
# ----------------------------------------------------------------------
COLOR_ALIASES = {      # spelling variants -> one standard word
    'grey': 'gray',
    'navy': 'blue',
    'maroon': 'red',
    'violet': 'purple',
    'golden': 'gold',
}
IGNORED_COLOR_WORDS = {'and', 'with', 'dark', 'light', 'deep', 'pale', 'bright'}


def normalize_color(value):
    """'Dark Navy & Red' -> {'blue', 'red'}"""
    words = normalize_text(value).split()
    words = [w for w in words if w not in IGNORED_COLOR_WORDS]
    return {COLOR_ALIASES.get(w, w) for w in words}


def color_similarity(color_a, color_b):
    """Shared colours / all colours. 'Black and Red' vs 'Black' = 1/2 = 0.5"""
    a, b = normalize_color(color_a), normalize_color(color_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ----------------------------------------------------------------------
# C. Brand: same (ignoring case, spaces, punctuation) = 1.0, else 0.0
# ----------------------------------------------------------------------
def normalize_brand(value):
    """'boAt', 'BOAT', 'Bo-At ' -> 'boat'"""
    return re.sub(r'[^a-z0-9]', '', (value or '').lower())


def brand_similarity(brand_a, brand_b):
    """A missing brand on either side gives NO credit (no evidence)."""
    a, b = normalize_brand(brand_a), normalize_brand(brand_b)
    return 1.0 if a and a == b else 0.0


# ----------------------------------------------------------------------
# D. Location: project-defined distance rules
# ----------------------------------------------------------------------
SAME_PLACE = 1.0
SAME_ZONE = 0.75     # same building / area
NEARBY_ZONE = 0.5    # neighbouring areas
FAR = 0.2

# Group campus places into zones. EDIT these to match your real campus.
ZONES = {
    'ACADEMIC': {'LIBRARY', 'MAIN_BUILDING', 'CLASSROOM_BLOCK',
                 'COMPUTER_LAB', 'AUDITORIUM'},
    'FACILITIES': {'CANTEEN', 'SPORTS_GROUND'},
    'ENTRANCE': {'PARKING', 'MAIN_GATE'},
}
# Pairs of zones that are close to each other
NEARBY_ZONES = [
    {'ACADEMIC', 'FACILITIES'},
]
LOCATION_TO_ZONE = {place: zone for zone, places in ZONES.items() for place in places}


def location_similarity(loc_a, loc_b):
    if not loc_a or not loc_b:
        return 0.0
    if loc_a == loc_b:
        # 'OTHER' on both sides could be two different places
        return NEARBY_ZONE if loc_a == 'OTHER' else SAME_PLACE
    zone_a = LOCATION_TO_ZONE.get(loc_a)
    zone_b = LOCATION_TO_ZONE.get(loc_b)
    if zone_a is None or zone_b is None:   # 'OTHER' = unknown place
        return FAR
    if zone_a == zone_b:
        return SAME_ZONE
    if {zone_a, zone_b} in NEARBY_ZONES:
        return NEARBY_ZONE
    return FAR


# ----------------------------------------------------------------------
# E. Time: the closer in time, the higher the score
# ----------------------------------------------------------------------
HOUR_TIERS = [        # (max hours apart, score)
    (1, 1.0),
    (3, 0.9),
    (6, 0.8),
    (24, 0.6),
    (72, 0.4),        # 3 days
    (168, 0.2),       # 7 days
]
DAY_TIERS = [         # used when a time of day is missing: (max days apart, score)
    (0, 0.8),
    (1, 0.6),
    (3, 0.4),
    (7, 0.2),
]


def _lookup(tiers, amount):
    for limit, score in tiers:
        if amount <= limit:
            return score
    return 0.0


def time_gap_hours(date_a, time_a, date_b, time_b):
    """Signed gap in hours (b minus a), or None if a time of day is missing.
    With a = lost and b = found, a positive number means 'found AFTER lost'."""
    if date_a is None or date_b is None or time_a is None or time_b is None:
        return None
    start = datetime.combine(date_a, time_a)
    end = datetime.combine(date_b, time_b)
    return (end - start).total_seconds() / 3600


def time_similarity(date_a, time_a, date_b, time_b):
    if date_a is None or date_b is None:
        return 0.0
    gap = time_gap_hours(date_a, time_a, date_b, time_b)
    if gap is not None:
        return _lookup(HOUR_TIERS, abs(gap))
    return _lookup(DAY_TIERS, abs((date_b - date_a).days))   # dates only


# ----------------------------------------------------------------------
# All five at once
# ----------------------------------------------------------------------
def compute_metadata_scores(lost, found):
    """Compare a lost item with a found item.
    Works with any object that has these attributes (a real Item or a test object)."""
    return {
        'category': category_similarity(lost.category, found.category),
        'color': color_similarity(lost.color, found.color),
        'brand': brand_similarity(lost.brand, found.brand),
        'location': location_similarity(lost.location, found.location),
        'time': time_similarity(lost.date, lost.time, found.date, found.time),
    }