import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from items.models import Item
from matcher.services.matching_service import CLOSED_STATUSES, find_visible_matches

ICONS = {'good': '[+]', 'bad': '[x]', 'neutral': '[-]'}

open_lost = Item.objects.filter(item_type=Item.LOST).exclude(status__in=CLOSED_STATUSES)

for lost in open_lost:
    print(f'\nLOST: {lost.title} (reported by {lost.user.username})')
    results = find_visible_matches(lost)
    if not results:
        print('   no matches scoring 40 or more')
    for rank, r in enumerate(results, start=1):
        print(f'   #{rank}  {r.final_score:5.1f}%  {r.label}  ->  {r.found.title}')
        for reason in r.reasons:
            print(f'        {ICONS[reason.kind]} {reason.text}')