from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from items.models import Item
from matcher.services.verification_service import start_claim

from .test_match_results import PASSWORD, ExampleDataMixin
from .test_matching_service import make_item
# ExampleDataMixin gives us: alice (owner), bob (finder), alice's lost earbuds,
# bob's found earbuds and bob's found backpack.


class SecurityTests(ExampleDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user('carol', password=PASSWORD)   # a stranger

    def login(self, name):
        self.client.login(username=name, password=PASSWORD)

    def test_every_page_needs_a_login(self):
        pages = [
            ('report_lost', []), ('report_found', []), ('my_reports', []),
            ('browse_items', []), ('claims', []), ('notification_list', []),
            ('mark_all_read', []), ('profile', []), ('dashboard', []),
            ('item_detail', [self.lost.pk]), ('item_edit', [self.lost.pk]),
            ('item_delete', [self.lost.pk]), ('item_change_status', [self.lost.pk]),
            ('item_matches', [self.lost.pk]),
            ('claim_start', [self.lost.pk, self.found_earbuds.pk]),
            ('claim_detail', [1]), ('claim_action', [1]),
        ]
        for name, args in pages:
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn('/accounts/login/', response.url, name)

    def test_csrf_protection_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username='alice', password=PASSWORD)
        self.assertEqual(client.post(reverse('logout')).status_code, 403)
        response = client.post(reverse('item_delete', args=[self.lost.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Item.objects.filter(pk=self.lost.pk).exists())

    def test_scripts_in_reports_are_escaped(self):
        evil = make_item(self.alice, Item.LOST, title='<script>alert(1)</script>')
        self.login('bob')
        response = self.client.get(reverse('item_detail', args=[evil.pk]))
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_strangers_cannot_touch_other_peoples_reports(self):
        self.login('carol')
        for name in ('item_edit', 'item_delete', 'item_matches'):
            response = self.client.get(reverse(name, args=[self.lost.pk]))
            self.assertEqual(response.status_code, 404, name)
        response = self.client.post(reverse('item_change_status', args=[self.lost.pk]),
                                    {'status': 'CLOSED'})
        self.assertEqual(response.status_code, 404)
        self.lost.refresh_from_db()
        self.assertEqual(self.lost.status, Item.LOST)

    def test_claim_pages_are_private(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        self.login('carol')
        self.assertEqual(
            self.client.get(reverse('claim_detail', args=[match.pk])).status_code, 404)
        response = self.client.post(reverse('claim_action', args=[match.pk]),
                                    {'action': 'approve'})
        self.assertEqual(response.status_code, 404)

    def test_nobody_can_claim_someone_elses_lost_report(self):
        self.login('carol')
        url = reverse('claim_start', args=[self.lost.pk, self.found_earbuds.pk])
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_the_session_cookie_is_not_readable_by_scripts(self):
        response = self.client.post(
            reverse('login'), {'username': 'alice', 'password': PASSWORD})
        self.assertTrue(response.cookies['sessionid']['httponly'])

    def test_login_text_that_looks_like_sql_does_not_log_anyone_in(self):
        response = self.client.post(
            reverse('login'), {'username': "alice' OR '1'='1", 'password': "x' OR '1'='1"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)