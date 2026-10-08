"""Scoring: combines the six similarity scores into ONE match score (0-100).

The weights and the labels below are PROJECT-DEFINED choices. They are not
scientifically validated, and the final score is NOT a probability that two
reports describe the same object. It is a ranking score.
"""

# How much each part counts. They add up to 1.0 (= 100%).
WEIGHTS = {
    'description': 0.30,
    'category': 0.20,
    'location': 0.15,
    'color': 0.15,
    'brand': 0.10,
    'time': 0.10,
}

# (minimum score, label), checked from the top down
LABELS = [
    (85, 'Very strong match'),
    (70, 'Strong match'),
    (40, 'Possible match'),
    (0, 'Low similarity'),
]

MIN_MATCH_SCORE = 40   # below this, a pair will not be shown as a match (used in 8B)


def calculate_final_score(scores):
    """scores: a dict with a 0.0-1.0 value for each name in WEIGHTS.
    Returns a number from 0.0 to 100.0 (one decimal)."""
    total = sum(weight * scores.get(name, 0.0) for name, weight in WEIGHTS.items())
    return round(total * 100, 1)


def get_label(final_score):
    for minimum, label in LABELS:
        if final_score >= minimum:
            return label
    return LABELS[-1][1]