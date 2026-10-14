from datetime import time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from items.models import Item

DEMO_PASSWORD = 'CampusDemo#2026'
OWNER = 'demo_owner'      # loses things
FINDER = 'demo_finder'    # finds things

# (who, type, title, category, brand, colour, description, location, days ago, time)
REPORTS = [
    (OWNER, 'LOST', 'Black boAt earbuds', 'ELECTRONICS', 'boAt', 'Black',
     'Black wireless earbuds in a small black charging case, scratch on the lid.',
     'LIBRARY', 1, time(14, 30)),
    (OWNER, 'LOST', 'Blue steel water bottle', 'OTHER', 'Milton', 'Blue',
     'Blue steel water bottle with a dent near the bottom and a white sticker on the side.',
     'CANTEEN', 1, time(13, 0)),
    (OWNER, 'LOST', 'Brown leather wallet', 'WALLETS', 'Fastrack', 'Brown',
     'Brown leather wallet with student ID card and two bank cards inside.',
     'CLASSROOM_BLOCK', 2, time(11, 15)),
    (OWNER, 'LOST', 'Bike key with red keychain', 'KEYS', '', 'Red and Black',
     'Motorcycle key with a red rubber keychain and a small bottle opener.',
     'PARKING', 2, None),
    (FINDER, 'FOUND', 'Black Bluetooth earbuds', 'ELECTRONICS', 'boAt', 'Black',
     'Black Bluetooth earbuds with a charging case, found on a reading table near the window.',
     'LIBRARY', 1, time(15, 0)),
    (FINDER, 'FOUND', 'Blue water bottle', 'OTHER', 'Milton', 'Blue',
     'Blue steel water bottle with a sticker, found on a table in the canteen.',
     'CANTEEN', 1, time(14, 0)),
    (FINDER, 'FOUND', 'Brown wallet', 'WALLETS', '', 'Brown',
     'Brown wallet with some cards inside, found on a bench near the main building.',
     'MAIN_BUILDING', 1, None),
    (FINDER, 'FOUND', 'Red backpack', 'BAGS', '', 'Red',
     'Red backpack with a white zip and a water bottle pocket.',
     'PARKING', 1, None),
    (FINDER, 'FOUND', 'Set of keys on a red ring', 'KEYS', '', 'Red',
     'Motorcycle key and two small keys on a red keychain.',
     'PARKING', 2, time(17, 30)),
    (FINDER, 'LOST', 'Black Casio watch', 'ACCESSORIES', 'Casio', 'Black',
     'Black digital Casio watch with a rubber strap and a cracked glass.',
     'SPORTS_GROUND', 3, time(16, 0)),
    (OWNER, 'FOUND', 'Black digital watch', 'ACCESSORIES', 'Casio', 'Black',
     'Black digital watch with a rubber strap, found near the sports ground.',
     'SPORTS_GROUND', 3, time(18, 0)),
]


class Command(BaseCommand):
    help = 'Create demo users and sample lost/found reports (safe to run again).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete the demo users (and their reports) first, then create them again.')

    def handle(self, *args, **options):
        if options['reset']:
            User.objects.filter(username__in=[OWNER, FINDER]).delete()   # reports go too

        users = {}
        for name in (OWNER, FINDER):
            user, created = User.objects.get_or_create(
                username=name, defaults={'email': f'{name}@example.com'})
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users[name] = user

        today = timezone.localdate()
        created_count = 0
        for who, kind, title, category, brand, colour, text, place, days_ago, at in REPORTS:
            _, created = Item.objects.get_or_create(
                user=users[who], title=title, item_type=kind,
                defaults={
                    'status': kind, 'category': category, 'brand': brand, 'color': colour,
                    'description': text, 'location': place,
                    'date': today - timedelta(days=days_ago), 'time': at,
                })
            created_count += created

        self.stdout.write(self.style.SUCCESS(
            f'Demo data ready: {created_count} new report(s). '
            f'Log in as {OWNER} or {FINDER} with password {DEMO_PASSWORD}'))