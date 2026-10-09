from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from items.models import Item

from .models import Match, Verification
from .services.explanations import build_reasons
from .services.matching_service import CLOSED_STATUSES, find_visible_matches
from .services.scoring import MIN_MATCH_SCORE
from .services.verification_service import (
    ClaimError,
    answer_question,
    approve_claim,
    ask_question,
    available_actions,
    claim_state,
    reject_claim,
    start_claim,
    withdraw_claim,
)


# ------------------------------------------------------------ match results
@login_required
def item_matches(request, pk):
    # user=request.user: only the OWNER of a report can see its matches
    item = get_object_or_404(Item, pk=pk, user=request.user)
    is_open = item.status not in CLOSED_STATUSES
    results = find_visible_matches(item) if is_open else []

    cards = []
    for result in results:
        state, claim = claim_state(result.lost, result.found)
        cards.append({
            'result': result,
            'other': result.other_item(item),
            'claim_state': state,       # 'active', 'rejected', 'busy' or 'available'
            'claim_match': claim,
        })

    return render(request, 'matcher/matches.html', {
        'item': item,
        'cards': cards,
        'is_open': is_open,
        'is_owner_view': item.item_type == Item.LOST,   # only lost owners can claim
        'min_score': MIN_MATCH_SCORE,
    })


# ------------------------------------------------------------------ claims
def _get_participant_match(user, pk):
    match = get_object_or_404(
        Match.objects.select_related('lost_item__user', 'found_item__user'), pk=pk)
    if user.pk not in (match.lost_item.user_id, match.found_item.user_id):
        raise Http404   # only the two people involved may see a claim
    return match


@login_required
def claims(request):
    matches = Match.objects.filter(
        Q(lost_item__user=request.user) | Q(found_item__user=request.user)
    ).select_related('lost_item__user', 'found_item__user')
    rows = [
        {'match': m, 'role': 'owner' if m.lost_item.user_id == request.user.pk else 'finder'}
        for m in matches
    ]
    return render(request, 'matcher/claims.html', {'rows': rows})


@login_required
@require_POST
def claim_start(request, lost_pk, found_pk):
    lost = get_object_or_404(Item, pk=lost_pk, user=request.user)   # owner only
    found = get_object_or_404(Item, pk=found_pk)
    try:
        match = start_claim(lost, found, request.user)
    except ClaimError as error:
        messages.error(request, str(error))
        return redirect('item_matches', pk=lost.pk)
    messages.success(request, 'Claim started. The finder will now ask you a private question.')
    return redirect('claim_detail', pk=match.pk)


@login_required
def claim_detail(request, pk):
    match = _get_participant_match(request.user, pk)
    is_owner = request.user.pk == match.lost_item.user_id
    verifications = list(match.verifications.all())
    open_question = next((v for v in verifications if v.status == Verification.ASKED), None)

    return render(request, 'matcher/claim.html', {
        'match': match,
        'is_owner': is_owner,
        'can': available_actions(match, request.user),
        'verifications': verifications,
        'open_question': open_question,
        # Contact details are only shown on the page when the claim is CONFIRMED
        'other_user': match.found_item.user if is_owner else match.lost_item.user,
        'reasons': build_reasons(match.lost_item, match.found_item, match.scores),
    })


# function, does it need text?, message shown on success
ACTIONS = {
    'ask': (ask_question, True, 'Question sent.'),
    'answer': (answer_question, True, 'Answer sent.'),
    'approve': (approve_claim, False,
                'Claim approved. Contact details are now visible to both of you.'),
    'reject': (reject_claim, False, 'Claim rejected. Both reports are open again.'),
    'withdraw': (withdraw_claim, False, 'Claim withdrawn. Both reports are open again.'),
}


@login_required
@require_POST
def claim_action(request, pk):
    match = _get_participant_match(request.user, pk)
    action = ACTIONS.get(request.POST.get('action'))
    if action is None:
        messages.error(request, 'Unknown action.')
        return redirect('claim_detail', pk=match.pk)

    function, needs_text, success_message = action
    try:
        if needs_text:
            function(match, request.user, request.POST.get('text', ''))
        else:
            function(match, request.user)
    except ClaimError as error:
        messages.error(request, str(error))   # e.g. "Only the finder can do this."
    else:
        messages.success(request, success_message)
    return redirect('claim_detail', pk=match.pk)