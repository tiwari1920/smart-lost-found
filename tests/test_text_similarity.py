from django.test import SimpleTestCase

from matcher.services.text_similarity import (
    shared_keywords,
    text_similarities,
    text_similarity,
)


class TextSimilarityTests(SimpleTestCase):
    def test_identical_texts(self):
        self.assertAlmostEqual(text_similarity('black earbuds', 'black earbuds'), 1.0)

    def test_word_order_and_case_do_not_matter(self):
        self.assertAlmostEqual(text_similarity('Black EARBUDS', 'earbuds black'), 1.0)

    def test_unrelated_texts(self):
        score = text_similarity('black wireless earbuds', 'red backpack with zip')
        self.assertEqual(score, 0.0)

    def test_similar_descriptions_score_in_the_middle(self):
        lost = ('Black boAt earbuds Black wireless earbuds in a small black '
                'charging case, scratch on the lid.')
        found = ('Black Bluetooth earbuds Black Bluetooth earbuds with a charging '
                 'case, found on a reading table near the window.')
        score = text_similarity(lost, found)
        self.assertGreater(score, 0.3)
        self.assertLess(score, 0.6)

    def test_one_query_many_candidates(self):
        scores = text_similarities('black earbuds', [
            'black earbuds with case',
            'red backpack with zip',
            'black bluetooth earbuds',
        ])
        self.assertEqual(len(scores), 3)
        self.assertGreater(scores[0], 0.0)
        self.assertEqual(scores[1], 0.0)
        self.assertGreater(scores[2], 0.0)

    def test_empty_text_gives_zero(self):
        self.assertEqual(text_similarity('', 'black earbuds'), 0.0)
        self.assertEqual(text_similarity('the and of', 'black earbuds'), 0.0)
        self.assertEqual(text_similarity('the and', 'of the'), 0.0)

    def test_no_candidates(self):
        self.assertEqual(text_similarities('black earbuds', []), [])

    def test_shared_keywords(self):
        words = shared_keywords('Black boAt earbuds in the library',
                                'Black Bluetooth earbuds found in the library')
        self.assertEqual(words, ['black', 'earbuds', 'library'])