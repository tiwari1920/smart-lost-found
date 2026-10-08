from datetime import date, time

from django.test import SimpleTestCase

from items.models import Item
from matcher.services.explanations import build_reasons, format_hours
from matcher.services.metadata_similarity import compute_metadata_scores
from matcher.services.scoring import calculate_final_score, score_breakdown
from matcher.services.text_similarity import item_text, text_similarity

TODAY = date(2026, 10, 7)


def make(item_type, **kwargs):
    """An unsaved Item (no database needed)."""
    values = dict(
        title='Black boAt earbuds',
        description='Black wireless earbuds with a charging case',
        category='ELECTRONICS', brand='boAt', color='Black',
        location='LIBRARY', date=TODAY, time=time(14, 30),
    )
    values.update(kwargs)
    return Item(item_type=item_type, **values)


def reasons_for(lost, found):
    """Run the same steps as the engine and return the reasons by topic."""
    scores = compute_metadata_scores(lost, found)
    scores['description'] = text_similarity(item_text(lost), item_text(found))
    return {reason.topic: reason for reason in build_reasons(lost, found, scores)}


class ReasonTests(SimpleTestCase):
    def setUp(self):
        self.lost = make(Item.LOST)

    def test_identical_reports_give_all_good_reasons(self):
        reasons = reasons_for(self.lost, make(Item.FOUND))
        self.assertEqual(len(reasons), 6)
        for reason in reasons.values():
            self.assertEqual(reason.kind, 'good', reason)
        self.assertEqual(reasons['category'].text, 'Same category (Electronics)')

    def test_different_category(self):
        reasons = reasons_for(self.lost, make(Item.FOUND, category='BAGS'))
        self.assertEqual(reasons['category'].kind, 'bad')
        self.assertEqual(reasons['category'].text, 'Different category (Electronics vs Bags)')

    def test_colour_levels(self):
        same = reasons_for(self.lost, make(Item.FOUND, color='black'))
        partly = reasons_for(self.lost, make(Item.FOUND, color='Black and Red'))
        different = reasons_for(self.lost, make(Item.FOUND, color='Red'))
        self.assertEqual(same['color'].text, 'Same colour (Black)')
        self.assertTrue(partly['color'].text.startswith('Partly matching colour'))
        self.assertEqual(different['color'].kind, 'bad')

    def test_location_levels(self):
        def text_for(place):
            return reasons_for(self.lost, make(Item.FOUND, location=place))['location'].text

        self.assertEqual(text_for('LIBRARY'), 'Same location (Library)')
        self.assertEqual(text_for('COMPUTER_LAB'), 'Same area (Library and Computer Lab)')
        self.assertEqual(text_for('CANTEEN'), 'Nearby locations (Library and Canteen)')
        self.assertEqual(text_for('PARKING'),
                         'Far-apart or unknown locations (Library and Parking Area)')

    def test_description_reason_lists_shared_words(self):
        text = reasons_for(self.lost, make(Item.FOUND))['description'].text
        self.assertTrue(text.startswith('Very similar description'))
        self.assertIn('earbuds', text)

    def test_description_with_little_overlap(self):
        found = make(Item.FOUND, title='Red backpack', description='Red backpack with a white zip')
        reason = reasons_for(self.lost, found)['description']
        self.assertEqual(reason.kind, 'bad')
        self.assertEqual(reason.text, 'Descriptions share few words')

    def test_brand_levels(self):
        same = reasons_for(self.lost, make(Item.FOUND, brand='BOAT'))
        missing = reasons_for(self.lost, make(Item.FOUND, brand=''))
        different = reasons_for(self.lost, make(Item.FOUND, brand='Sony'))
        self.assertEqual(same['brand'].text, 'Same brand (boAt)')
        self.assertEqual(missing['brand'].kind, 'neutral')
        self.assertEqual(missing['brand'].text, 'Brand not given on both reports')
        self.assertEqual(different['brand'].text, 'Different brand (boAt vs Sony)')

    def test_time_after_lost(self):
        reason = reasons_for(self.lost, make(Item.FOUND, time=time(15, 0)))['time']
        self.assertEqual(reason.kind, 'good')
        self.assertEqual(reason.text, 'Found 30 minutes after it was reported lost')

    def test_time_days_apart_is_bad(self):
        reason = reasons_for(self.lost, make(Item.FOUND, date=date(2026, 10, 10)))['time']
        self.assertEqual(reason.kind, 'bad')
        self.assertEqual(reason.text, 'Found 3 days after it was reported lost')

    def test_time_without_time_of_day(self):
        lost = make(Item.LOST, time=None)
        reason = reasons_for(lost, make(Item.FOUND))['time']
        self.assertEqual(reason.kind, 'good')
        self.assertEqual(reason.text, 'Same day (time of day not given on both reports)')

    def test_format_hours(self):
        self.assertEqual(format_hours(0.5), '30 minutes')
        self.assertEqual(format_hours(-0.5), '30 minutes')
        self.assertEqual(format_hours(1), '1 hour')
        self.assertEqual(format_hours(2), '2 hours')
        self.assertEqual(format_hours(50), '2 days')

    def test_breakdown_adds_up_to_the_final_score(self):
        scores = {'description': 0.47, 'category': 1.0, 'location': 1.0,
                  'color': 1.0, 'brand': 1.0, 'time': 1.0}
        rows = score_breakdown(scores)
        self.assertEqual([row['name'] for row in rows],
                         ['Description', 'Category', 'Location', 'Colour', 'Brand', 'Time'])
        self.assertEqual(sum(row['weight'] for row in rows), 100)
        self.assertAlmostEqual(sum(row['points'] for row in rows),
                               calculate_final_score(scores), places=1)