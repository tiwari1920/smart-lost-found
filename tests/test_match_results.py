from datetime import time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from items.models import Item
from matcher.services.matching_service import find_visible_matches

from .test_matching_service import make_item

PASSWORD = 'x12345678'


class ExampleDataMixin:
    """Alice lost earbuds. Bob found matching earbuds and an unrelated backpack."""

    def setUp(self):
        self.alice = User.objects.create_user('alice', password=PASSWORD)
        self.bob = User.objects.create_user('bob', password=PASSWORD)
        self.lost = make_item(
            self.alice, Item.LOST, title='Black boAt earbuds', category='ELECTRONICS',
            brand='boAt', color='Black', location='LIBRARY', time=time(14, 30),
            description='Black wireless earbuds in a small black charging case, '
                        'scratch on the lid.')
        self.found_earbuds = make_item(
            self.bob, Item.FOUND, title='Black Bluetooth earbuds', category='ELECTRONICS',
            brand='boAt', color='Black', location='LIBRARY', time=time(15, 0),
            description='Black Bluetooth earbuds with a charging case, found on a '
                        'reading table near the window.')
        self.found_backpack = make_item(
            self.bob, Item.FOUND, title='Red backpack', category='BAGS', color='Red',
            location='PARKING',
            description='Red backpack with a white zip and a water bottle pocket.')


class VisibleMatchesTests(ExampleDataMixin, TestCase):
    def test_low_scores_are_hidden(self):
        results = find_visible_matches(self.lost)
        self.assertEqual([r.found for r in results], [self.found_earbuds])


class MatchesPageTests(ExampleDataMixin, TestCase):
    def url_for(self, item):
        return reverse('item_matches', args=[item.pk])

    def test_login_is_required(self):
        response = self.client.get(self.url_for(self.lost))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_owner_sees_matches_and_reasons(self):
        self.client.login(username='alice', password=PASSWORD)
        response = self.client.get(self.url_for(self.lost))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Black Bluetooth earbuds')
        self.assertContains(response, 'Same category')
        self.assertContains(response, 'How was this score calculated?')
        self.assertNotContains(response, 'Red backpack')

    def test_other_users_get_404(self):
        self.client.login(username='bob', password=PASSWORD)
        response = self.client.get(self.url_for(self.lost))
        self.assertEqual(response.status_code, 404)

    def test_finder_sees_the_lost_report_as_a_match(self):
        self.client.login(username='bob', password=PASSWORD)
        response = self.client.get(self.url_for(self.found_earbuds))
        self.assertContains(response, 'Black boAt earbuds')

    def test_page_explains_when_there_are_no_matches(self):
        self.client.login(username='bob', password=PASSWORD)
        response = self.client.get(self.url_for(self.found_backpack))
        self.assertContains(response, 'No possible matches yet')

    def test_closed_report_is_not_matched(self):
        self.lost.status = Item.CLOSED
        self.lost.save()
        self.client.login(username='alice', password=PASSWORD)
        response = self.client.get(self.url_for(self.lost))
        self.assertContains(response, 'no longer matched')


class ReportRedirectTests(ExampleDataMixin, TestCase):
    def post_data(self, **overrides):
        data = {
            'title': 'Black earbuds', 'category': 'ELECTRONICS', 'brand': 'boAt',
            'color': 'Black', 'location': 'LIBRARY',
            'description': 'Black wireless earbuds with a charging case',
            'date': timezone.localdate().isoformat(), 'time': '15:00',
        }
        data.update(overrides)
        return data

    def test_reporting_lost_with_matches_goes_to_the_matches_page(self):
        User.objects.create_user('carol', password=PASSWORD)
        self.client.login(username='carol', password=PASSWORD)
        response = self.client.post(reverse('report_lost'), self.post_data())
        self.assertEqual(response.status_code, 302)
        self.assertIn('/matches/item/', response.url)

    def test_reporting_lost_without_matches_goes_to_the_detail_page(self):
        User.objects.create_user('carol', password=PASSWORD)
        self.client.login(username='carol', password=PASSWORD)
        data = self.post_data(title='Green umbrella', category='OTHER', brand='',
                              color='Green', location='MAIN_GATE',
                              description='Long green umbrella with a wooden handle')
        response = self.client.post(reverse('report_lost'), data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/items/', response.url)
        self.assertNotIn('/matches/', response.url)

    def test_reporting_found_with_matches_goes_to_the_matches_page(self):
        User.objects.create_user('dave', password=PASSWORD)
        self.client.login(username='dave', password=PASSWORD)
        response = self.client.post(reverse('report_found'), self.post_data())
        self.assertEqual(response.status_code, 302)
        self.assertIn('/matches/item/', response.url)