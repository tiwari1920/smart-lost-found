import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from items.models import Item
from matcher.services.text_similarity import item_text, shared_keywords, text_similarities

found_items = list(Item.objects.filter(item_type=Item.FOUND))

for lost in Item.objects.filter(item_type=Item.LOST):
    print(f'\nLOST: {lost.title}')
    scores = text_similarities(item_text(lost), [item_text(f) for f in found_items])
    ranked = sorted(zip(scores, found_items), key=lambda pair: pair[0], reverse=True)
    for score, found in ranked:
        words = ', '.join(shared_keywords(item_text(lost), item_text(found))) or '-'
        print(f'   {score:.2f}  {found.title}   (shared words: {words})')