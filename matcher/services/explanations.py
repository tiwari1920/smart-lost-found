"""Explanations: turns the numbers of a match into plain-English reasons.

Every reason has a topic, a kind and a text:
  kind 'good'    -> shown with a green tick  (evidence FOR a match)
  kind 'bad'     -> shown with a red cross   (evidence AGAINST a match)
  kind 'neutral' -> shown with a grey dash   (not enough information)

The reasons are built from the SAME scores that make the final number,
so the explanation can never disagree with the score.
"""
from collections import namedtuple

from .metadata_similarity import NEARBY_ZONE, SAME_PLACE, SAME_ZONE, time_gap_hours
from .text_similarity import item_text, shared_keywords

Reason = namedtuple('Reason', ['topic', 'kind', 'text'])

GOOD, BAD, NEUTRAL = 'good', 'bad', 'neutral'


def _plural(number, word):
    return f'{number} {word}' if number == 1 else f'{number} {word}s'


def format_hours(hours):
    """0.5 -> '30 minutes', 2 -> '2 hours', 50 -> '2 days'."""
    hours = abs(hours)
    if hours < 1:
        return _plural(max(1, round(hours * 60)), 'minute')
    if hours < 48:
        return _plural(round(hours), 'hour')
    return _plural(round(hours / 24), 'day')


def _category_reason(lost, found, scores):
    if scores['category'] >= 1.0:
        return Reason('category', GOOD, f'Same category ({lost.get_category_display()})')
    return Reason('category', BAD, 'Different category '
                  f'({lost.get_category_display()} vs {found.get_category_display()})')


def _color_reason(lost, found, scores):
    score = scores['color']
    if score >= 1.0:
        return Reason('color', GOOD, f'Same colour ({lost.color})')
    if score > 0:
        return Reason('color', GOOD, f'Partly matching colour ({lost.color} vs {found.color})')
    return Reason('color', BAD, f'Different colour ({lost.color} vs {found.color})')


def _location_reason(lost, found, scores):
    place_a, place_b = lost.get_location_display(), found.get_location_display()
    score = scores['location']
    if score >= SAME_PLACE:
        return Reason('location', GOOD, f'Same location ({place_a})')
    if score >= SAME_ZONE:
        return Reason('location', GOOD, f'Same area ({place_a} and {place_b})')
    if score >= NEARBY_ZONE:
        return Reason('location', GOOD, f'Nearby locations ({place_a} and {place_b})')
    return Reason('location', BAD, f'Far-apart or unknown locations ({place_a} and {place_b})')


def _description_reason(lost, found, scores):
    score = scores['description']
    words = shared_keywords(item_text(lost), item_text(found))
    shared = f' (shared words: {", ".join(words[:6])})' if words else ''
    if score >= 0.5:
        return Reason('description', GOOD, f'Very similar description{shared}')
    if score >= 0.25:
        return Reason('description', GOOD, f'Similar description{shared}')
    return Reason('description', BAD, f'Descriptions share few words{shared}')


def _brand_reason(lost, found, scores):
    if scores['brand'] >= 1.0:
        return Reason('brand', GOOD, f'Same brand ({lost.brand})')
    if not lost.brand.strip() or not found.brand.strip():
        return Reason('brand', NEUTRAL, 'Brand not given on both reports')
    return Reason('brand', BAD, f'Different brand ({lost.brand} vs {found.brand})')


def _time_reason(lost, found, scores):
    kind = GOOD if scores['time'] >= 0.6 else BAD
    gap = time_gap_hours(lost.date, lost.time, found.date, found.time)  # found minus lost
    if gap is not None:
        if abs(gap) * 60 < 1:
            text = 'Found at about the same time it was reported lost'
        elif gap > 0:
            text = f'Found {format_hours(gap)} after it was reported lost'
        else:
            text = f'Found {format_hours(gap)} before the reported loss time'
    else:
        days = (found.date - lost.date).days
        if days == 0:
            text = 'Same day (time of day not given on both reports)'
        elif days > 0:
            text = f'Found {_plural(days, "day")} after the loss date'
        else:
            text = f'Found {_plural(-days, "day")} before the loss date'
    return Reason('time', kind, text)


def build_reasons(lost, found, scores):
    """Explain a match. `scores` holds the six sub-scores (0.0-1.0).
    Returns six Reason objects, in the order shown to the user."""
    return [
        _category_reason(lost, found, scores),
        _color_reason(lost, found, scores),
        _location_reason(lost, found, scores),
        _description_reason(lost, found, scores),
        _brand_reason(lost, found, scores),
        _time_reason(lost, found, scores),
    ]