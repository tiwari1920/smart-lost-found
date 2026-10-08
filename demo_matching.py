import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from items.models import Item
from matcher.services.matching_service import CLOSED_STATUSES, find_matches_for

open_lost = Item.objects.filter(item_type=Item.LOST).exclude(status__in=CLOSED_STATUSES)

for lost in open_lost:
    print(f'\nLOST: {lost.title} (reported by {lost.user.username})')
    results = find_matches_for(lost)
    if not results:
        print('   no candidates (needs open FOUND reports from OTHER users)')
    for rank, r in enumerate(results, start=1):
        s = r.scores
        print(f'   #{rank}  {r.final_score:5.1f}%  {r.label:<18} {r.found.title}')
        print(f'        description={s["description"]:.2f}  category={s["category"]:.2f}  '
              f'location={s["location"]:.2f}  color={s["color"]:.2f}  '
              f'brand={s["brand"]:.2f}  time={s["time"]:.2f}')