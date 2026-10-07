import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()  # loads Django so a plain script can use the database

from items.models import Item
from matcher.services.metadata_similarity import compute_metadata_scores

lost_items = Item.objects.filter(item_type=Item.LOST)
found_items = Item.objects.filter(item_type=Item.FOUND)

for lost in lost_items:
    print(f'LOST: {lost.title} ({lost.get_location_display()}, {lost.date})')
    for found in found_items:
        print(f'   vs FOUND: {found.title}')
        print(f'      {compute_metadata_scores(lost, found)}')