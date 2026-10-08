from datetime import date, time

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from items.models import Item
from matcher.services.matching_service import find_matches_for
from matcher.services.text_similarity import text_similarities

TODAY = date(2026, 10, 7)


def make_item(user, item_type, **kwargs):
    """Create an Item in the temporary test database."""
    values = dict(
        title='Item', category='OTHER', brand='', color='black',
        description='something', location='LIBRARY', date=TODAY, time=None,
        status=item_type,   # a LOST item starts as 'LOST', a FOUND item as 'FOUND'
    )
    values.update(kwargs)
    return Item.objects.create(user=user, item_type=item_type, **values)


class CorpusTests(SimpleTestCase):
    def test_common_words_count_less_than_rare_words(self):
        corpus = ['black bag', 'black pen', 'black shoe', 'black wallet',
                  'black bluetooth earbuds', 'bluetooth speaker']
        scores = text_similarities(
            'black bluetooth earbuds',
            ['black wallet', 'bluetooth speaker'],
            corpus,
        )
        # 'black' is in almost every report, 'bluetooth' is rare
        self.assertGreater(scores[1], scores[0])


class MatchingServiceTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', password='x12345678')
        self.bob = User.objects.create_user('bob', password='x12345678')

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

    def test_earbuds_are_ranked_first(self):
        results = find_matches_for(self.lost)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].found, self.found_earbuds)
        self.assertGreater(results[0].final_score, results[1].final_score)

    def test_example_1_scores_as_strong_match(self):
        top = find_matches_for(self.lost)[0]
        self.assertGreaterEqual(top.final_score, 70)
        self.assertIn(top.label, ('Strong match', 'Very strong match'))

    def test_example_2_scores_as_low_similarity(self):
        results = find_matches_for(self.lost)
        backpack = [r for r in results if r.found == self.found_backpack][0]
        self.assertLess(backpack.final_score, 40)
        self.assertEqual(backpack.label, 'Low similarity')

    def test_own_reports_are_never_matched(self):
        make_item(self.alice, Item.FOUND, title='Black earbuds', category='ELECTRONICS')
        results = find_matches_for(self.lost)
        self.assertEqual(len(results), 2)   # still only bob's two reports

    def test_closed_reports_are_skipped(self):
        self.found_earbuds.status = Item.RECOVERED
        self.found_earbuds.save()
        results = find_matches_for(self.lost)
        self.assertEqual([r.found for r in results], [self.found_backpack])

    def test_closed_query_returns_nothing(self):
        self.lost.status = Item.CLOSED
        self.lost.save()
        self.assertEqual(find_matches_for(self.lost), [])

    def test_search_works_from_the_found_side(self):
        results = find_matches_for(self.found_earbuds)
        self.assertEqual(len(results), 1)           # only alice's lost earbuds
        self.assertEqual(results[0].lost, self.lost)

    def test_same_score_from_either_side(self):
        from_lost = find_matches_for(self.lost)[0]
        from_found = find_matches_for(self.found_earbuds)[0]
        self.assertEqual(from_lost.final_score, from_found.final_score)