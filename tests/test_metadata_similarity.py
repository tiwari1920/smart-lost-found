from datetime import date, time
from types import SimpleNamespace

from django.test import SimpleTestCase

from items.models import Item
from matcher.services.metadata_similarity import (
    ZONES,
    brand_similarity,
    category_similarity,
    color_similarity,
    compute_metadata_scores,
    location_similarity,
    time_similarity,
)

TODAY = date(2026, 10, 7)


def make_item(**kwargs):
    """A simple stand-in for an Item (no database needed)."""
    values = dict(category='', color='', brand='', location='', date=TODAY, time=None)
    values.update(kwargs)
    return SimpleNamespace(**values)


class CategoryTests(SimpleTestCase):
    def test_same_category(self):
        self.assertEqual(category_similarity('ELECTRONICS', 'ELECTRONICS'), 1.0)

    def test_different_category(self):
        self.assertEqual(category_similarity('ELECTRONICS', 'BAGS'), 0.0)


class ColorTests(SimpleTestCase):
    def test_case_does_not_matter(self):
        self.assertEqual(color_similarity('Black', 'BLACK'), 1.0)
        self.assertEqual(color_similarity('black', ' Black '), 1.0)

    def test_spelling_variants(self):
        self.assertEqual(color_similarity('Grey', 'gray'), 1.0)

    def test_shade_words_are_ignored(self):
        self.assertEqual(color_similarity('Dark Blue', 'blue'), 1.0)

    def test_partial_overlap(self):
        self.assertAlmostEqual(color_similarity('Black and Red', 'Black'), 0.5)

    def test_different_colors(self):
        self.assertEqual(color_similarity('Black', 'Red'), 0.0)

    def test_missing_color(self):
        self.assertEqual(color_similarity('', 'Red'), 0.0)


class BrandTests(SimpleTestCase):
    def test_case_and_punctuation_do_not_matter(self):
        self.assertEqual(brand_similarity('boAt', 'BOAT'), 1.0)
        self.assertEqual(brand_similarity('Boat', 'bo-at'), 1.0)

    def test_different_brand(self):
        self.assertEqual(brand_similarity('boAt', 'Sony'), 0.0)

    def test_missing_brand_gets_no_credit(self):
        self.assertEqual(brand_similarity('boAt', ''), 0.0)
        self.assertEqual(brand_similarity('', ''), 0.0)


class LocationTests(SimpleTestCase):
    def test_same_place(self):
        self.assertEqual(location_similarity('LIBRARY', 'LIBRARY'), 1.0)

    def test_same_zone(self):
        self.assertEqual(location_similarity('LIBRARY', 'COMPUTER_LAB'), 0.75)

    def test_nearby_zones(self):
        self.assertEqual(location_similarity('LIBRARY', 'CANTEEN'), 0.5)

    def test_far_apart(self):
        self.assertEqual(location_similarity('LIBRARY', 'PARKING'), 0.2)

    def test_unknown_place(self):
        self.assertEqual(location_similarity('LIBRARY', 'OTHER'), 0.2)

    def test_every_location_has_a_zone(self):
        """Guards against typos if the location list is edited later."""
        zoned = set().union(*ZONES.values())
        for value, _label in Item.LOCATION_CHOICES:
            if value != 'OTHER':
                self.assertIn(value, zoned)


class TimeTests(SimpleTestCase):
    def test_thirty_minutes_apart(self):
        self.assertEqual(time_similarity(TODAY, time(14, 30), TODAY, time(15, 0)), 1.0)

    def test_five_hours_apart(self):
        self.assertEqual(time_similarity(TODAY, time(9, 0), TODAY, time(14, 0)), 0.8)

    def test_twenty_hours_apart(self):
        next_day = date(2026, 10, 8)
        self.assertEqual(time_similarity(TODAY, time(14, 30), next_day, time(10, 30)), 0.6)

    def test_ten_days_apart(self):
        later = date(2026, 10, 17)
        self.assertEqual(time_similarity(TODAY, time(10, 0), later, time(10, 0)), 0.0)

    def test_missing_time_uses_dates_only(self):
        self.assertEqual(time_similarity(TODAY, None, TODAY, time(15, 0)), 0.8)
        self.assertEqual(time_similarity(TODAY, None, date(2026, 10, 8), None), 0.6)


class SpecExampleTests(SimpleTestCase):
    def test_example_1_same_earbuds(self):
        lost = make_item(category='ELECTRONICS', color='Black', brand='boAt',
                         location='LIBRARY', time=time(14, 30))
        found = make_item(category='ELECTRONICS', color='Black', brand='Boat',
                          location='LIBRARY', time=time(15, 0))
        self.assertEqual(
            compute_metadata_scores(lost, found),
            {'category': 1.0, 'color': 1.0, 'brand': 1.0, 'location': 1.0, 'time': 1.0},
        )

    def test_example_2_earbuds_vs_backpack(self):
        lost = make_item(category='ELECTRONICS', color='Black', brand='boAt',
                         location='LIBRARY', time=time(14, 30))
        found = make_item(category='BAGS', color='Red', brand='',
                          location='PARKING', time=time(15, 0))
        scores = compute_metadata_scores(lost, found)
        self.assertEqual(scores['category'], 0.0)
        self.assertEqual(scores['color'], 0.0)
        self.assertEqual(scores['brand'], 0.0)
        self.assertEqual(scores['location'], 0.2)