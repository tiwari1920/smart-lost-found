"""The matching engine: finds and ranks possible matches for ONE report.

Steps for a report X:
1. Collect candidates: open reports of the OPPOSITE type, from OTHER users.
2. For each candidate compute the six similarity scores.
3. Combine them into a final score (0-100) and give it a label.
4. Sort, so the best match comes first.
"""
from dataclasses import dataclass

from items.models import Item

from .metadata_similarity import compute_metadata_scores
from .scoring import calculate_final_score, get_label
from .text_similarity import item_text, text_similarities

CLOSED_STATUSES = (Item.RECOVERED, Item.CLOSED)


@dataclass
class MatchResult:
    lost: Item
    found: Item
    scores: dict          # the six sub-scores, each 0.0-1.0
    final_score: float    # 0-100
    label: str

    def other_item(self, item):
        """The report on the OTHER side of this match, seen from `item`."""
        return self.found if item.pk == self.lost.pk else self.lost


def find_matches_for(item, limit=None):
    """Rank all open reports of the opposite type against `item`, best first."""
    if item.status in CLOSED_STATUSES:
        return []   # a closed report is not matched any more

    opposite_type = Item.FOUND if item.item_type == Item.LOST else Item.LOST
    open_items = Item.objects.exclude(status__in=CLOSED_STATUSES)
    candidates = list(
        open_items.filter(item_type=opposite_type)
        .exclude(user_id=item.user_id)      # never match a user's own reports
    )
    if not candidates:
        return []

    # Word weights (IDF) are learned from ALL open reports, so every pair is
    # scored the same way, whichever report starts the search.
    corpus = [item_text(i) for i in open_items]
    description_scores = text_similarities(
        item_text(item), [item_text(c) for c in candidates], corpus
    )

    results = []
    for candidate, description_score in zip(candidates, description_scores):
        lost, found = (item, candidate) if item.item_type == Item.LOST else (candidate, item)
        scores = compute_metadata_scores(lost, found)
        scores['description'] = description_score
        final_score = calculate_final_score(scores)
        results.append(MatchResult(lost, found, scores, final_score, get_label(final_score)))

    results.sort(key=lambda r: r.final_score, reverse=True)
    return results[:limit] if limit else results