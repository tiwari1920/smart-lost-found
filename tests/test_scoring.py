from django.test import SimpleTestCase

from matcher.services.scoring import WEIGHTS, calculate_final_score, get_label


class ScoringTests(SimpleTestCase):
    def test_weights_add_up_to_one(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0)

    def test_perfect_scores_give_100(self):
        scores = {name: 1.0 for name in WEIGHTS}
        self.assertEqual(calculate_final_score(scores), 100.0)

    def test_zero_scores_give_0(self):
        scores = {name: 0.0 for name in WEIGHTS}
        self.assertEqual(calculate_final_score(scores), 0.0)

    def test_formula_with_known_numbers(self):
        scores = {'description': 0.5, 'category': 1.0, 'location': 1.0,
                  'color': 1.0, 'brand': 1.0, 'time': 1.0}
        # 0.5*0.30 + 0.20 + 0.15 + 0.15 + 0.10 + 0.10 = 0.85
        self.assertEqual(calculate_final_score(scores), 85.0)

    def test_missing_scores_count_as_zero(self):
        self.assertEqual(calculate_final_score({'category': 1.0}), 20.0)

    def test_labels_at_the_boundaries(self):
        self.assertEqual(get_label(0), 'Low similarity')
        self.assertEqual(get_label(39.9), 'Low similarity')
        self.assertEqual(get_label(40), 'Possible match')
        self.assertEqual(get_label(69.9), 'Possible match')
        self.assertEqual(get_label(70), 'Strong match')
        self.assertEqual(get_label(84.9), 'Strong match')
        self.assertEqual(get_label(85), 'Very strong match')
        self.assertEqual(get_label(100), 'Very strong match')