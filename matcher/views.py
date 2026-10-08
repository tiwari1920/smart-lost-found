from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from items.models import Item

from .services.matching_service import CLOSED_STATUSES, find_visible_matches
from .services.scoring import MIN_MATCH_SCORE


@login_required
def item_matches(request, pk):
    # user=request.user: only the OWNER of a report can see its matches
    item = get_object_or_404(Item, pk=pk, user=request.user)
    is_open = item.status not in CLOSED_STATUSES
    results = find_visible_matches(item) if is_open else []

    # Templates can't call a method with an argument, so we prepare the
    # "other side" of each match here.
    cards = [{'result': r, 'other': r.other_item(item)} for r in results]

    return render(request, 'matcher/matches.html', {
        'item': item,
        'cards': cards,
        'is_open': is_open,
        'min_score': MIN_MATCH_SCORE,
    })