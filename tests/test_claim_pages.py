from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from items.models import Item
from matcher.models import Match
from matcher.services.verification_service import start_claim

from .test_match_results import PASSWORD, ExampleDataMixin


class ClaimPagesTests(ExampleDataMixin, TestCase):
    def setUp(self):
        super().setUp()   # alice (owner), bob (finder) and the reports
        User.objects.filter(pk=self.alice.pk).update(email='alice@example.com')
        User.objects.filter(pk=self.bob.pk).update(email='bob@example.com')
        User.objects.create_user('carol', password=PASSWORD)   # a stranger

    def login(self, name):
        self.client.login(username=name, password=PASSWORD)

    def start_url(self):
        return reverse('claim_start', args=[self.lost.pk, self.found_earbuds.pk])

    def do(self, match, who, action, text=''):
        """Log in as `who` and press a button on the claim page."""
        self.login(who)
        return self.client.post(reverse('claim_action', args=[match.pk]),
                                {'action': action, 'text': text}, follow=True)

    def test_claims_page_requires_login(self):
        response = self.client.get(reverse('claims'))
        self.assertEqual(response.status_code, 302)

    def test_matches_page_offers_the_claim_button(self):
        self.login('alice')
        response = self.client.get(reverse('item_matches', args=[self.lost.pk]))
        self.assertContains(response, 'This is mine')

    def test_owner_starts_a_claim(self):
        self.login('alice')
        response = self.client.post(self.start_url())
        match = Match.objects.get()
        self.assertRedirects(response, reverse('claim_detail', args=[match.pk]))
        self.found_earbuds.refresh_from_db()
        self.assertEqual(self.found_earbuds.status, Item.VERIFICATION_PENDING)

    def test_only_the_owner_can_start_a_claim(self):
        self.login('bob')
        response = self.client.post(self.start_url())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Match.objects.count(), 0)

    def test_claim_page_is_only_for_the_two_people(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        url = reverse('claim_detail', args=[match.pk])
        for name, expected in (('alice', 200), ('bob', 200), ('carol', 404)):
            self.login(name)
            self.assertEqual(self.client.get(url).status_code, expected, name)

    def test_each_person_sees_only_their_own_buttons(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        url = reverse('claim_detail', args=[match.pk])
        self.login('bob')
        response = self.client.get(url)
        self.assertContains(response, 'Ask a question')
        self.assertContains(response, 'Reject claim')
        self.assertNotContains(response, 'Withdraw claim')
        self.login('alice')
        response = self.client.get(url)
        self.assertContains(response, 'Withdraw claim')
        self.assertNotContains(response, 'Ask a question')

    def test_contact_details_appear_only_after_approval(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        url = reverse('claim_detail', args=[match.pk])

        self.login('alice')
        self.assertNotContains(self.client.get(url), 'bob@example.com')

        self.do(match, 'bob', 'ask', 'Which colour is the case?')
        self.do(match, 'alice', 'answer', 'Black')
        self.login('alice')
        self.assertNotContains(self.client.get(url), 'bob@example.com')   # not approved yet

        self.do(match, 'bob', 'approve')
        match.refresh_from_db()
        self.assertEqual(match.status, Match.CONFIRMED)

        self.login('alice')
        self.assertContains(self.client.get(url), 'bob@example.com')
        self.login('bob')
        self.assertContains(self.client.get(url), 'alice@example.com')

    def test_wrong_role_gets_an_error_message(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        response = self.do(match, 'alice', 'ask', 'Can I ask myself?')
        self.assertContains(response, 'Only the person who found the item')
        self.assertEqual(match.verifications.count(), 0)

    def test_rejecting_reopens_the_reports(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        self.do(match, 'bob', 'reject')
        match.refresh_from_db()
        self.assertEqual(match.status, Match.REJECTED)
        self.lost.refresh_from_db()
        self.assertEqual(self.lost.status, Item.LOST)

    def test_claims_list_shows_the_claim_to_both_people(self):
        start_claim(self.lost, self.found_earbuds, self.alice)
        for name in ('alice', 'bob'):
            self.login(name)
            self.assertContains(self.client.get(reverse('claims')), 'Black Bluetooth earbuds')

    def test_matches_pages_link_to_the_claim_after_it_starts(self):
        start_claim(self.lost, self.found_earbuds, self.alice)
        self.login('alice')
        response = self.client.get(reverse('item_matches', args=[self.lost.pk]))
        self.assertContains(response, 'Open verification')
        self.assertNotContains(response, 'This is mine')
        self.login('bob')
        response = self.client.get(reverse('item_matches', args=[self.found_earbuds.pk]))
        self.assertContains(response, 'Open verification')