from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from items.models import Item
from matcher.models import Match
from matcher.services.matching_service import find_matches_for, find_visible_matches
from matcher.services.verification_service import (
    ClaimError,
    admin_cancel_claim,
    reject_claim,
    start_claim,
)
from notifications.models import Notification

from .helpers import report_data
from .test_match_results import PASSWORD, ExampleDataMixin
# ExampleDataMixin gives us: alice (owner), bob (finder), alice's lost earbuds,
# bob's found earbuds and bob's found backpack.


class ModerationTests(ExampleDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_superuser('admin1', 'admin@example.com', PASSWORD)

    def login(self, name):
        self.client.login(username=name, password=PASSWORD)

    def hide(self, item):
        item.is_hidden = True
        item.save()

    def admin_action(self, url_name, action, *objects):
        """Log in as the admin and run an action from the admin list page."""
        self.login('admin1')
        return self.client.post(
            reverse(url_name),
            {'action': action, '_selected_action': [obj.pk for obj in objects]},
            follow=True,
        )

    # ---------------------------------------------------------- visibility
    def test_hidden_reports_are_not_listed_in_browse(self):
        self.hide(self.found_earbuds)
        self.login('alice')
        response = self.client.get(reverse('browse_items'))
        self.assertEqual(response.context['total'], 2)

    def test_hidden_reports_are_never_matched(self):
        self.hide(self.found_earbuds)
        results = find_matches_for(self.lost)
        self.assertEqual([r.found for r in results], [self.found_backpack])
        self.assertEqual(find_visible_matches(self.lost), [])
        self.assertEqual(find_matches_for(self.found_earbuds), [])

    def test_a_hidden_report_cannot_be_claimed(self):
        self.hide(self.found_earbuds)
        with self.assertRaises(ClaimError):
            start_claim(self.lost, self.found_earbuds, self.alice)

    def test_hidden_report_page_is_for_owner_and_staff_only(self):
        self.hide(self.found_earbuds)
        url = reverse('item_detail', args=[self.found_earbuds.pk])
        self.login('alice')
        self.assertEqual(self.client.get(url).status_code, 404)
        self.login('bob')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'hidden by an administrator')
        self.login('admin1')
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_users_cannot_hide_their_own_reports_through_the_form(self):
        self.login('alice')
        self.client.post(reverse('report_lost'),
                         report_data(title='Green umbrella', is_hidden='on'))
        item = Item.objects.get(title='Green umbrella')
        self.assertFalse(item.is_hidden)

    # ---------------------------------------------------------- admin actions
    def test_admin_can_hide_and_unhide_reports(self):
        response = self.admin_action('admin:items_item_changelist',
                                     'hide_reports', self.found_earbuds)
        self.assertEqual(response.status_code, 200)
        self.found_earbuds.refresh_from_db()
        self.assertTrue(self.found_earbuds.is_hidden)

        self.admin_action('admin:items_item_changelist', 'unhide_reports', self.found_earbuds)
        self.found_earbuds.refresh_from_db()
        self.assertFalse(self.found_earbuds.is_hidden)

    def test_admin_status_actions_skip_reports_in_an_active_claim(self):
        start_claim(self.lost, self.found_earbuds, self.alice)
        self.admin_action('admin:items_item_changelist', 'mark_recovered',
                          self.lost, self.found_backpack)
        self.lost.refresh_from_db()
        self.found_backpack.refresh_from_db()
        self.assertEqual(self.lost.status, Item.VERIFICATION_PENDING)   # skipped
        self.assertEqual(self.found_backpack.status, Item.RECOVERED)

    def test_admin_can_cancel_a_stuck_claim(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        self.admin_action('admin:matcher_match_changelist', 'cancel_claims', match)
        match.refresh_from_db()
        self.lost.refresh_from_db()
        self.found_earbuds.refresh_from_db()
        self.assertEqual(match.status, Match.WITHDRAWN)
        self.assertEqual(self.lost.status, Item.LOST)
        self.assertEqual(self.found_earbuds.status, Item.FOUND)
        for user in (self.alice, self.bob):   # both people are told
            self.assertEqual(
                Notification.objects.filter(
                    user=user, notification_type=Notification.CLAIM).count(), 1)

    def test_finished_claims_cannot_be_cancelled_and_normal_users_have_no_admin(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        reject_claim(match, self.bob)
        with self.assertRaises(ClaimError):
            admin_cancel_claim(match)

        self.login('alice')
        response = self.client.get(reverse('admin:items_item_changelist'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)