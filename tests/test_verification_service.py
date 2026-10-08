from django.test import TestCase

from items.models import Item
from matcher.models import Match, Verification
from matcher.services.verification_service import (
    MAX_QUESTIONS,
    ClaimError,
    answer_question,
    approve_claim,
    ask_question,
    reject_claim,
    start_claim,
    withdraw_claim,
)

from .test_match_results import ExampleDataMixin
# ExampleDataMixin gives us: alice (owner), bob (finder), alice's lost earbuds,
# bob's found earbuds and bob's found backpack.


class StartClaimTests(ExampleDataMixin, TestCase):
    def test_owner_can_start_a_claim(self):
        match = start_claim(self.lost, self.found_earbuds, self.alice)
        self.assertEqual(match.status, Match.VERIFICATION_PENDING)
        self.assertGreaterEqual(match.final_score, 70)
        self.assertGreater(match.description_score, 0)
        self.lost.refresh_from_db()
        self.found_earbuds.refresh_from_db()
        self.assertEqual(self.lost.status, Item.VERIFICATION_PENDING)
        self.assertEqual(self.found_earbuds.status, Item.VERIFICATION_PENDING)

    def test_only_the_owner_of_the_lost_report_can_claim(self):
        with self.assertRaises(ClaimError):
            start_claim(self.lost, self.found_earbuds, self.bob)
        self.assertEqual(Match.objects.count(), 0)

    def test_cannot_claim_an_item_that_is_not_a_match(self):
        with self.assertRaises(ClaimError):
            start_claim(self.lost, self.found_backpack, self.alice)

    def test_cannot_start_two_claims_for_the_same_pair(self):
        start_claim(self.lost, self.found_earbuds, self.alice)
        with self.assertRaises(ClaimError):
            start_claim(self.lost, self.found_earbuds, self.alice)


class QuestionTests(ExampleDataMixin, TestCase):
    def setUp(self):
        super().setUp()   # creates alice, bob and the three reports
        self.match = start_claim(self.lost, self.found_earbuds, self.alice)

    def test_finder_asks_and_owner_answers(self):
        question = ask_question(self.match, self.bob, 'What sticker is on the lid?')
        self.assertEqual(question.status, Verification.ASKED)
        self.assertEqual(question.requester, self.alice)
        answered = answer_question(self.match, self.alice, 'A small blue star')
        self.assertEqual(answered.status, Verification.ANSWERED)
        self.assertEqual(answered.answer, 'A small blue star')

    def test_only_the_finder_can_ask(self):
        with self.assertRaises(ClaimError):
            ask_question(self.match, self.alice, 'Anything?')

    def test_only_the_owner_can_answer(self):
        ask_question(self.match, self.bob, 'Which colour is the case?')
        with self.assertRaises(ClaimError):
            answer_question(self.match, self.bob, 'Black')

    def test_one_open_question_at_a_time(self):
        ask_question(self.match, self.bob, 'First question?')
        with self.assertRaises(ClaimError):
            ask_question(self.match, self.bob, 'Second question?')

    def test_question_limit(self):
        for number in range(MAX_QUESTIONS):
            ask_question(self.match, self.bob, f'Question {number}?')
            answer_question(self.match, self.alice, 'An answer')
        with self.assertRaises(ClaimError):
            ask_question(self.match, self.bob, 'One too many?')

    def test_empty_text_is_refused(self):
        with self.assertRaises(ClaimError):
            ask_question(self.match, self.bob, '   ')
        ask_question(self.match, self.bob, 'A real question?')
        with self.assertRaises(ClaimError):
            answer_question(self.match, self.alice, '')


class DecisionTests(ExampleDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.match = start_claim(self.lost, self.found_earbuds, self.alice)

    def test_cannot_approve_before_an_answer(self):
        with self.assertRaises(ClaimError):
            approve_claim(self.match, self.bob)
        ask_question(self.match, self.bob, 'Which colour is the case?')
        with self.assertRaises(ClaimError):   # asked, but not answered yet
            approve_claim(self.match, self.bob)

    def test_finder_can_approve_after_an_answer(self):
        ask_question(self.match, self.bob, 'Which colour is the case?')
        answer_question(self.match, self.alice, 'Black')
        approve_claim(self.match, self.bob)
        self.match.refresh_from_db()
        self.assertEqual(self.match.status, Match.CONFIRMED)

    def test_owner_cannot_approve_their_own_claim(self):
        ask_question(self.match, self.bob, 'Which colour is the case?')
        answer_question(self.match, self.alice, 'Black')
        with self.assertRaises(ClaimError):
            approve_claim(self.match, self.alice)

    def test_rejecting_reopens_both_reports_and_blocks_a_retry(self):
        reject_claim(self.match, self.bob)
        self.lost.refresh_from_db()
        self.found_earbuds.refresh_from_db()
        self.assertEqual(self.lost.status, Item.LOST)
        self.assertEqual(self.found_earbuds.status, Item.FOUND)
        with self.assertRaises(ClaimError):
            start_claim(self.lost, self.found_earbuds, self.alice)

    def test_withdrawing_reopens_and_allows_a_new_claim(self):
        withdraw_claim(self.match, self.alice)
        self.lost.refresh_from_db()
        self.found_earbuds.refresh_from_db()
        self.assertEqual(self.lost.status, Item.LOST)
        new_match = start_claim(self.lost, self.found_earbuds, self.alice)
        self.assertNotEqual(new_match.pk, self.match.pk)

    def test_only_the_owner_can_withdraw(self):
        with self.assertRaises(ClaimError):
            withdraw_claim(self.match, self.bob)

    def test_finished_claims_cannot_be_changed(self):
        reject_claim(self.match, self.bob)
        with self.assertRaises(ClaimError):
            ask_question(self.match, self.bob, 'Too late?')