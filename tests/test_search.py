from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from items.models import Item
from items.views import ITEMS_PER_PAGE

from .helpers import PASSWORD
from .test_matching_service import make_item


class SearchTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', password=PASSWORD)
        self.bob = User.objects.create_user('bob', password=PASSWORD)
        make_item(self.alice, Item.LOST, title='Black boAt earbuds', category='ELECTRONICS',
                  brand='boAt', color='Black', location='LIBRARY', date=date(2026, 10, 5),
                  description='Wireless earbuds in a black charging case')
        make_item(self.bob, Item.FOUND, title='Black Bluetooth earbuds', category='ELECTRONICS',
                  brand='boAt', color='Black', location='LIBRARY', date=date(2026, 10, 6),
                  description='Found on a reading table')
        make_item(self.bob, Item.FOUND, title='Red backpack', category='BAGS',
                  color='Red', location='PARKING', date=date(2026, 10, 6),
                  description='White zip and bottle pocket')
        self.client.login(username='alice', password=PASSWORD)

    def search(self, **params):
        return self.client.get(reverse('browse_items'), params)

    def total(self, **params):
        return self.search(**params).context['total']

    def test_login_is_required(self):
        self.client.logout()
        response = self.search()
        self.assertEqual(response.status_code, 302)

    def test_no_filters_lists_everything(self):
        self.assertEqual(self.total(), 3)
        self.assertEqual(self.total(q='   '), 3)    # a blank search is no search

    def test_keyword_search(self):
        self.assertEqual(self.total(q='earbuds'), 2)
        self.assertEqual(self.total(q='RED'), 1)          # case does not matter
        self.assertEqual(self.total(q='earbuds red'), 0)  # every word must match

    def test_type_filter(self):
        self.assertEqual(self.total(item_type='FOUND'), 2)
        self.assertEqual(self.total(item_type='LOST'), 1)

    def test_category_and_location_filters(self):
        self.assertEqual(self.total(category='BAGS'), 1)
        self.assertEqual(self.total(location='LIBRARY'), 2)

    def test_colour_and_brand_match_partly(self):
        self.assertEqual(self.total(color='bla'), 2)
        self.assertEqual(self.total(brand='boat'), 2)

    def test_status_filter(self):
        self.assertEqual(self.total(status='FOUND'), 2)
        self.assertEqual(self.total(status='RECOVERED'), 0)

    def test_filters_combine(self):
        self.assertEqual(self.total(item_type='FOUND', location='LIBRARY'), 1)

    def test_date_range(self):
        self.assertEqual(self.total(date_from='2026-10-06'), 2)
        self.assertEqual(self.total(date_to='2026-10-05'), 1)
        self.assertEqual(self.total(date_from='2027-01-01'), 0)

    def test_a_backwards_date_range_shows_an_error(self):
        response = self.search(date_from='2026-10-07', date_to='2026-10-01')
        self.assertEqual(response.context['total'], 0)
        self.assertContains(response, 'cannot be after')

    def test_a_value_that_is_not_in_the_list_gives_no_results(self):
        self.assertEqual(self.total(category='NOPE'), 0)

    def test_sql_injection_text_is_only_text(self):
        response = self.search(q="' OR 1=1 --")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 0)

    def test_scripts_typed_into_the_search_box_are_escaped(self):
        response = self.search(q='<script>alert(1)</script>')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<script>alert(1)</script>')


class PaginationTests(TestCase):
    def setUp(self):
        user = User.objects.create_user('alice', password=PASSWORD)
        for number in range(ITEMS_PER_PAGE + 1):     # one more than fits on a page
            make_item(user, Item.LOST, title=f'Report {number}')
        self.client.login(username='alice', password=PASSWORD)

    def test_reports_are_split_into_pages(self):
        first = self.client.get(reverse('browse_items'))
        self.assertEqual(len(first.context['page_obj']), ITEMS_PER_PAGE)
        second = self.client.get(reverse('browse_items'), {'page': 2})
        self.assertEqual(len(second.context['page_obj']), 1)

    def test_bad_page_numbers_do_not_crash(self):
        too_far = self.client.get(reverse('browse_items'), {'page': 999})
        self.assertEqual(too_far.status_code, 200)
        self.assertEqual(too_far.context['page_obj'].number, 2)     # the last page
        text = self.client.get(reverse('browse_items'), {'page': 'abc'})
        self.assertEqual(text.context['page_obj'].number, 1)

    def test_filters_are_kept_when_changing_pages(self):
        response = self.client.get(reverse('browse_items'), {'item_type': 'LOST', 'page': 2})
        self.assertEqual(response.context['query_string'], 'item_type=LOST')