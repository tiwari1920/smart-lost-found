"""Creates in-app notifications."""
from django.urls import reverse

from matcher.services.matching_service import find_visible_matches

from .models import Notification

# Only STRONG matches send a notification. Weaker ones are still listed on the
# matches page, so nobody is spammed. (Project-defined threshold.)
NOTIFY_MIN_SCORE = 70


def notify(user, message, notification_type, link=''):
    return Notification.objects.create(
        user=user,
        message=message[:255],
        notification_type=notification_type,
        link=link,
    )


def notify_new_matches(item):
    """A new report was saved: tell the owners of strong matches on the other side.
    Returns how many notifications were sent."""
    sent = 0
    for result in find_visible_matches(item):    # best match first
        if result.final_score < NOTIFY_MIN_SCORE:
            break                                # everything after this is weaker
        other = result.other_item(item)          # the report that belongs to someone else
        message = (
            f'New possible match for your {other.get_item_type_display().lower()} '
            f'report "{other.title}": "{item.title}" ({result.final_score}%).'
        )
        notify(other.user, message, Notification.MATCH,
               reverse('item_matches', args=[other.pk]))
        sent += 1
    return sent

# What to say, and to whom, when something happens in a claim.
# who: 'owner' = the person who lost the item, 'finder' = the person who found it,
#      'other' = whoever did NOT perform the action
CLAIM_EVENTS = {
    'started': ('finder', Notification.CLAIM,
                'A claim was started on your found item "{found}". Please ask a private question.'),
    'ask': ('owner', Notification.CLAIM,
            'The finder asked a private question about your claim for "{lost}".'),
    'answer': ('finder', Notification.CLAIM,
               'The owner answered your question about "{found}".'),
    'approve': ('owner', Notification.CLAIM,
                'Your claim for "{lost}" was approved. Contact details are now visible.'),
    'reject': ('owner', Notification.CLAIM,
               'Your claim for "{lost}" was rejected.'),
    'withdraw': ('finder', Notification.CLAIM,
                 'The owner withdrew the claim on your found item "{found}".'),
    'recover': ('other', Notification.RECOVERY,
                'The handover of "{found}" was marked as complete. Both reports are now Recovered.'),
}


def notify_claim_event(match, event, actor=None):
    """Tell the right person about something that happened in a claim."""
    who, notification_type, template = CLAIM_EVENTS[event]
    owner, finder = match.lost_item.user, match.found_item.user
    if who == 'owner':
        recipient = owner
    elif who == 'finder':
        recipient = finder
    else:                                    # 'other': not the person who did it
        recipient = finder if actor.pk == owner.pk else owner
    message = template.format(lost=match.lost_item.title, found=match.found_item.title)
    notify(recipient, message, notification_type, reverse('claim_detail', args=[match.pk]))