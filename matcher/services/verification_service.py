"""Ownership verification: the rules of a claim.

The story:
1. The owner of a LOST report starts a claim on a matching FOUND report.
2. The finder asks a private question that only the real owner could answer.
3. The owner answers.
4. The finder approves or rejects the claim.
Contact details are shown only after approval (Day 9B).

Every function checks WHO may do the action and WHICH state the claim must be in.
A wrong action raises ClaimError, whose message is safe to show to the user.
"""
from django.db.models import Q

from items.models import Item
from matcher.models import Match, Verification

from .matching_service import CLOSED_STATUSES, find_visible_matches

MAX_QUESTIONS = 3        # per claim, so nobody can be pestered endlessly
MAX_TEXT_LENGTH = 300
ACTIVE_STATUSES = (Match.VERIFICATION_PENDING, Match.CONFIRMED)


class ClaimError(Exception):
    """An action is not allowed. The message can be shown to the user."""


# ------------------------------------------------------------------ helpers
def _set_status(item, new_status):
    item.status = new_status
    item.save(update_fields=['status', 'updated_at'])


def _reopen_items(match):
    """After a rejected or withdrawn claim, both reports are open again."""
    for item, open_status in ((match.lost_item, Item.LOST), (match.found_item, Item.FOUND)):
        if item.status == Item.VERIFICATION_PENDING:
            _set_status(item, open_status)


def _require_pending(match):
    if match.status != Match.VERIFICATION_PENDING:
        raise ClaimError('This claim is no longer active.')


def _require_finder(match, user):
    if user.pk != match.found_item.user_id:
        raise ClaimError('Only the person who found the item can do this.')


def _require_owner(match, user):
    if user.pk != match.lost_item.user_id:
        raise ClaimError('Only the owner who made the claim can do this.')


def _clean_text(text, what):
    text = (text or '').strip()
    if not text:
        raise ClaimError(f'Please write {what}.')
    if len(text) > MAX_TEXT_LENGTH:
        raise ClaimError(f'Please keep it under {MAX_TEXT_LENGTH} characters.')
    return text


# ------------------------------------------------------------------ actions
def start_claim(lost, found, user):
    """The owner of `lost` claims the matching `found` report."""
    if user.pk != lost.user_id:
        raise ClaimError('Only the owner of a lost report can claim an item.')
    if lost.item_type != Item.LOST or found.item_type != Item.FOUND:
        raise ClaimError('A claim needs one lost report and one found report.')
    if lost.status in CLOSED_STATUSES or found.status in CLOSED_STATUSES:
        raise ClaimError('One of these reports is already closed.')

    busy = Match.objects.filter(status__in=ACTIVE_STATUSES).filter(
        Q(lost_item=lost) | Q(found_item=found))
    if busy.exists():
        raise ClaimError('A claim for one of these reports is already being verified.')
    if Match.objects.filter(lost_item=lost, found_item=found, status=Match.REJECTED).exists():
        raise ClaimError('An earlier claim for this item was rejected.')

    # Only items the engine really suggests can be claimed
    result = next((r for r in find_visible_matches(lost) if r.found.pk == found.pk), None)
    if result is None:
        raise ClaimError('This item is not a current match for your report.')

    s = result.scores
    match = Match.objects.create(
        lost_item=lost, found_item=found,
        description_score=s['description'], category_score=s['category'],
        color_score=s['color'], brand_score=s['brand'],
        location_score=s['location'], time_score=s['time'],
        final_score=result.final_score,
    )
    _set_status(lost, Item.VERIFICATION_PENDING)
    _set_status(found, Item.VERIFICATION_PENDING)
    return match


def ask_question(match, user, question):
    """The finder asks a private question."""
    _require_finder(match, user)
    _require_pending(match)
    question = _clean_text(question, 'a question')
    if match.verifications.filter(status=Verification.ASKED).exists():
        raise ClaimError('Please wait for the answer to your last question.')
    if match.verifications.count() >= MAX_QUESTIONS:
        raise ClaimError(f'You can ask at most {MAX_QUESTIONS} questions. Please approve or reject.')
    return Verification.objects.create(
        match=match, requester=match.lost_item.user, question=question)


def answer_question(match, user, answer):
    """The owner answers the open question."""
    _require_owner(match, user)
    _require_pending(match)
    open_question = match.verifications.filter(status=Verification.ASKED).first()
    if open_question is None:
        raise ClaimError('There is no question to answer right now.')
    open_question.answer = _clean_text(answer, 'an answer')
    open_question.status = Verification.ANSWERED
    open_question.save()
    return open_question


def approve_claim(match, user):
    """The finder accepts that the claimant is the owner."""
    _require_finder(match, user)
    _require_pending(match)
    if match.verifications.filter(status=Verification.ASKED).exists():
        raise ClaimError('Wait for the answer to your question before deciding.')
    if not match.verifications.filter(status=Verification.ANSWERED).exists():
        raise ClaimError('Ask at least one question and read the answer before approving.')
    match.status = Match.CONFIRMED
    match.save(update_fields=['status'])
    return match


def reject_claim(match, user):
    """The finder refuses the claim (allowed at any time while it is pending)."""
    _require_finder(match, user)
    _require_pending(match)
    match.status = Match.REJECTED
    match.save(update_fields=['status'])
    _reopen_items(match)
    return match


def withdraw_claim(match, user):
    """The owner takes the claim back."""
    _require_owner(match, user)
    _require_pending(match)
    match.status = Match.WITHDRAWN
    match.save(update_fields=['status'])
    _reopen_items(match)
    return match

    # ------------------------------------------------------------------ for the pages
def claim_state(lost, found):
    """What is the situation for this lost/found pair? Returns (state, match).
    state is 'active' (a claim exists), 'rejected', 'busy' or 'available'."""
    pair = Match.objects.filter(lost_item=lost, found_item=found)
    active = pair.filter(status__in=ACTIVE_STATUSES).first()
    if active:
        return 'active', active
    if pair.filter(status=Match.REJECTED).exists():
        return 'rejected', None
    busy = Match.objects.filter(status__in=ACTIVE_STATUSES).filter(
        Q(lost_item=lost) | Q(found_item=found))
    if busy.exists():
        return 'busy', None
    return 'available', None


def available_actions(match, user):
    """Which buttons should this person see? (The same rules as above.)"""
    actions = set()
    if match.status != Match.VERIFICATION_PENDING:
        return actions

    questions = list(match.verifications.all())
    has_open = any(q.status == Verification.ASKED for q in questions)
    has_answer = any(q.status == Verification.ANSWERED for q in questions)

    if user.pk == match.found_item.user_id:          # the finder
        actions.add('reject')
        if not has_open and len(questions) < MAX_QUESTIONS:
            actions.add('ask')
        if has_answer and not has_open:
            actions.add('approve')
    elif user.pk == match.lost_item.user_id:         # the owner
        actions.add('withdraw')
        if has_open:
            actions.add('answer')
    return actions