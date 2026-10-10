from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from items.models import Item
from matcher.models import Match
from matcher.services.matching_service import find_visible_matches
from matcher.services.verification_service import (
    ClaimError,
    answer_question,
    approve_claim,
    ask_question,
    available_actions,
    complete_recovery,
    reject_claim,
    start_claim,
)
from notifications.models import Notification

from .test_match_results import PASSWORD, ExampleDataMixin


class RecoveryServiceTests(ExampleDataMixin, TestCase):
    def make_approved_claim(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        ask_question(match, self.bob, 'Which colour is the case?')
        answer_question(match, self.alice, 'Black')
        approve_claim(match, self.bob)
        return match

    def assert_both_recovered(self):
        self.lost.refresh_from_db()
        self.found_earbuds.refresh_from_db()
        self.assertEqual(self.lost.status, Item.RECOVERED)
        self.assertEqual(self.found_earbuds.status, Item.RECOVERED)

    def test_owner_can_complete(self):
        match = self.make_approved_claim()
        complete_recovery(match, self.alice)
        match.refresh_from_db()
        self.assertEqual(match.status, Match.COMPLETED)
        self.assert_both_recovered()

    def test_finder_can_complete(self):
        match = self.make_approved_claim()
        complete_recovery(match, self.bob)
        self.assert_both_recovered()

    def test_cannot_complete_before_approval(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        with self.assertRaises(ClaimError):
            complete_recovery(match, self.alice)

    def test_strangers_cannot_complete(self):
        carol = User.objects.create_user('carol', password=PASSWORD)
        match = self.make_approved_claim()
        with self.assertRaises(ClaimError):
            complete_recovery(match, carol)

    def test_cannot_complete_twice(self):
        match = self.make_approved_claim()
        complete_recovery(match, self.alice)
        with self.assertRaises(ClaimError):
            complete_recovery(match, self.bob)

    def test_recovered_reports_are_no_longer_matched(self):
        match = self.make_approved_claim()
        complete_recovery(match, self.alice)
        self.lost.refresh_from_db()
        self.assertEqual(find_visible_matches(self.lost), [])

    def test_available_actions_follow_the_state(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        self.assertEqual(available_actions(match, self.bob), {'reject', 'ask'})
        self.assertEqual(available_actions(match, self.alice), {'withdraw'})
        ask_question(match, self.bob, 'Which colour is the case?')
        answer_question(match, self.alice, 'Black')
        approve_claim(match, self.bob)
        self.assertEqual(available_actions(match, self.alice), {'recover'})
        self.assertEqual(available_actions(match, self.bob), {'recover'})


class RecoveryPageTests(ExampleDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        User.objects.filter(pk=self.alice.pk).update(email='alice@example.com')
        User.objects.filter(pk=self.bob.pk).update(email='bob@example.com')

    def login(self, name):
        self.client.login(username=name, password=PASSWORD)

    def do(self, match, who, action, text=''):
        """Log in as `who` and press a button on the claim page."""
        self.login(who)
        return self.client.post(reverse('claim_action', args=[match.pk]),
                                {'action': action, 'text': text}, follow=True)

    def test_each_claim_step_notifies_the_other_person(self):
        self.login('alice')
        self.client.post(reverse('claim_start', args=[self.lost.pk, self.found_earbuds.pk]))
        match = Match.objects.get()
        self.do(match, 'bob', 'ask', 'Which colour is the case?')
        self.do(match, 'alice', 'answer', 'Black')
        self.do(match, 'bob', 'approve')
        self.do(match, 'alice', 'recover')

        alice_messages = list(Notification.objects.filter(user=self.alice)
                              .values_list('message', flat=True))
        bob_messages = list(Notification.objects.filter(user=self.bob)
                            .values_list('message', flat=True))
        self.assertEqual(len(alice_messages), 2)   # the question and the approval
        self.assertEqual(len(bob_messages), 3)     # claim started, answer, handover
        self.assertTrue(any('private question' in m for m in alice_messages))
        self.assertTrue(any('approved' in m for m in alice_messages))
        self.assertTrue(any('claim was started' in m for m in bob_messages))
        self.assertTrue(any('answered' in m for m in bob_messages))
        self.assertEqual(
            Notification.objects.filter(user=self.bob,
                                        notification_type=Notification.RECOVERY).count(), 1)

    def test_failed_action_sends_no_notification(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        self.do(match, 'alice', 'ask', 'The owner cannot ask')
        self.assertEqual(Notification.objects.count(), 0)

    def test_recover_button_appears_only_after_approval(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        url = reverse('claim_detail', args=[match.pk])
        self.login('alice')
        self.assertNotContains(self.client.get(url), 'mark as recovered')

        ask_question(match, self.bob, 'Which colour is the case?')
        answer_question(match, self.alice, 'Black')
        approve_claim(match, self.bob)
        self.assertContains(self.client.get(url), 'mark as recovered')
        self.login('bob')
        self.assertContains(self.client.get(url), 'mark as recovered')

        self.do(match, 'bob', 'recover')
        response = self.client.get(url)
        self.assertContains(response, 'Item recovered')
        self.assertNotContains(response, 'mark as recovered')
        self.assertNotContains(response, 'alice@example.com')   # contact details hidden again

    def test_cannot_delete_a_report_in_an_active_claim(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        self.login('alice')
        response = self.client.post(reverse('item_delete', args=[self.lost.pk]))
        self.assertRedirects(response, reverse('claim_detail', args=[match.pk]))
        self.assertTrue(Item.objects.filter(pk=self.lost.pk).exists())

    def test_cannot_close_a_report_in_an_active_claim(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        self.login('alice')
        response = self.client.post(reverse('item_change_status', args=[self.lost.pk]),
                                    {'status': 'CLOSED'})
        self.assertRedirects(response, reverse('claim_detail', args=[match.pk]))
        self.lost.refresh_from_db()
        self.assertEqual(self.lost.status, Item.VERIFICATION_PENDING)

    def test_report_can_be_deleted_once_the_claim_is_rejected(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        reject_claim(match, self.bob)
        self.login('alice')
        response = self.client.post(reverse('item_delete', args=[self.lost.pk]))
        self.assertRedirects(response, reverse('my_reports'))
        self.assertFalse(Item.objects.filter(pk=self.lost.pk).exists())

    def test_item_page_hides_status_buttons_during_a_claim(self):
        start_claim(self.lost, self.found_earbuds, self.alice)
        self.login('alice')
        response = self.client.get(reverse('item_detail', args=[self.lost.pk]))
        self.assertContains(response, 'part of a claim')
        self.assertNotContains(response, 'Mark as recovered')
        self.assertNotContains(response, 'Delete')