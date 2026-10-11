"""Statistics for the admin dashboard. Plain counting with the Django ORM."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone

from items.models import Item
from matcher.models import Match


def _top(queryset, field, labels, limit=5):
    """The most common values of `field`, as rows with a label, a count
    and a bar width (percent of the biggest count)."""
    rows = list(
        queryset.values(field).annotate(count=Count('id')).order_by('-count', field)[:limit]
    )
    biggest = rows[0]['count'] if rows else 1
    return [
        {
            'label': labels.get(row[field], row[field]),
            'count': row['count'],
            'percent': round(row['count'] * 100 / biggest),
        }
        for row in rows
    ]


def _breakdown(model, status_values_counts, choices, skip=()):
    """One row per status, including statuses with a count of 0."""
    counts = dict(status_values_counts)
    return [
        {'label': label, 'count': counts.get(value, 0)}
        for value, label in choices
        if value not in skip
    ]


def get_statistics():
    items = Item.objects.all()
    lost = items.filter(item_type=Item.LOST)
    found = items.filter(item_type=Item.FOUND)

    lost_total = lost.count()
    recovered = lost.filter(status=Item.RECOVERED).count()   # lost items returned to their owners
    week_ago = timezone.now() - timedelta(days=7)

    item_status_counts = items.values_list('status').annotate(total=Count('id'))
    claim_status_counts = Match.objects.values_list('status').annotate(total=Count('id'))

    return {
        'users': User.objects.count(),
        'lost_total': lost_total,
        'found_total': found.count(),
        'recovered': recovered,
        'recovery_rate': round(recovered * 100 / lost_total) if lost_total else 0,
        'recent_reports': items.filter(created_at__gte=week_ago).count(),
        'open_claims': Match.objects.filter(
            status__in=(Match.VERIFICATION_PENDING, Match.CONFIRMED)).count(),
        'top_categories': _top(items, 'category', dict(Item.CATEGORY_CHOICES)),
        'top_lost_locations': _top(lost, 'location', dict(Item.LOCATION_CHOICES)),
        'status_rows': _breakdown(Item, item_status_counts, Item.STATUS_CHOICES,
                                  skip=(Item.POTENTIAL_MATCH,)),
        'claim_rows': _breakdown(Match, claim_status_counts, Match.STATUS_CHOICES),
    }