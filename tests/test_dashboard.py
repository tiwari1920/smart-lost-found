from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from items.models import Item
from matcher.services.verification_service import start_claim

from .test_match_results import PASSWORD, ExampleDataMixin
from dashboard.services import get_statistics
# The example data: alice lost earbuds; bob found earbuds and a backpack.


class StatisticsTests(ExampleDataMixin, TestCase):
    def test_totals(self):
        stats = get_statistics()
        self.assertEqual(stats['users'], 2)
        self.assertEqual(stats['lost_total'], 1)
        self.assertEqual(stats['found_total'], 2)
        self.assertEqual(stats['recovered'], 0)
        self.assertEqual(stats['recovery_rate'], 0)

    def test_recovery_rate(self):
        self.lost.status = Item.RECOVERED
        self.lost.save()
        stats = get_statistics()
        self.assertEqual(stats['recovered'], 1)
        self.assertEqual(stats['recovery_rate'], 100)

    def test_top_categories(self):
        rows = get_statistics()['top_categories']
        self.assertEqual(rows[0], {'label': 'Electronics', 'count': 2, 'percent': 100})
        self.assertEqual(rows[1], {'label': 'Bags', 'count': 1, 'percent': 50})

    def test_top_lost_locations_ignore_found_reports(self):
        rows = get_statistics()['top_lost_locations']
        self.assertEqual(rows, [{'label': 'Library', 'count': 1, 'percent': 100}])

    def test_claim_counts(self):
        start_claim(self.lost, self.found_earbuds, self.alice)
        stats = get_statistics()
        self.assertEqual(stats['open_claims'], 1)
        pending = [r for r in stats['claim_rows'] if r['label'] == 'Verification pending']
        self.assertEqual(pending[0]['count'], 1)


class EmptyDatabaseTests(TestCase):
    def test_empty_database_gives_zeros(self):
        stats = get_statistics()
        self.assertEqual(stats['lost_total'], 0)
        self.assertEqual(stats['recovery_rate'], 0)     # no division by zero
        self.assertEqual(stats['top_categories'], [])
        self.assertEqual(stats['top_lost_locations'], [])


class DashboardPageTests(ExampleDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user('admin1', password=PASSWORD, is_staff=True)

    def login(self, name):
        self.client.login(username=name, password=PASSWORD)

    def test_login_is_required(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_normal_users_are_forbidden(self):
        self.login('alice')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_staff_sees_the_dashboard(self):
        self.login('admin1')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin dashboard')
        self.assertEqual(response.context['stats']['lost_total'], 1)
        self.assertEqual(response.context['stats']['users'], 3)

    def test_menu_link_is_only_for_staff(self):
        self.login('admin1')
        self.assertContains(self.client.get(reverse('home')), 'href="/dashboard/"')
        self.login('alice')
        self.assertNotContains(self.client.get(reverse('home')), 'href="/dashboard/"')