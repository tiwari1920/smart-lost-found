from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from items.models import Item
from matcher.services.matching_service import find_visible_matches


def seed(*flags):
    call_command('seed_demo', *flags, stdout=StringIO())


class SeedDemoTests(TestCase):
    def test_it_creates_users_and_eleven_reports(self):
        seed()
        self.assertEqual(User.objects.filter(username__startswith='demo_').count(), 2)
        self.assertEqual(Item.objects.count(), 11)
        self.assertEqual(Item.objects.filter(item_type=Item.LOST).count(), 5)

    def test_running_it_twice_does_not_duplicate(self):
        seed()
        seed()
        self.assertEqual(Item.objects.count(), 11)

    def test_reset_rebuilds_the_demo_accounts(self):
        seed()
        seed('--reset')
        self.assertEqual(Item.objects.count(), 11)

    def test_the_demo_users_can_log_in(self):
        seed()
        self.assertTrue(
            self.client.login(username='demo_owner', password='CampusDemo#2026'))

    def test_the_demo_earbuds_match_at_least_85(self):
        seed()
        lost = Item.objects.get(title='Black boAt earbuds')
        best = find_visible_matches(lost)[0]
        self.assertEqual(best.found.title, 'Black Bluetooth earbuds')
        self.assertGreaterEqual(best.final_score, 80)    # about 85 in the calibration
        self.assertEqual(best.label in ('Strong match', 'Very strong match'), True)


class ErrorPageTests(TestCase):
    def test_unknown_url_shows_the_friendly_404_page(self):
        response = self.client.get('/this-page-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'We could not find that page', status_code=404)