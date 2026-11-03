import unittest
import uuid
from datetime import date
from types import SimpleNamespace

from app.models.enums import MatchLevel
from app.services.matching_service import calculate_pair, date_score, overlap_score, tokens


class MatchingServiceTests(unittest.TestCase):
    def setUp(self):
        category_id = uuid.uuid4()
        self.lost = SimpleNamespace(
            category_id=category_id,
            area="Block B Cafeteria",
            event_date=date(2026, 10, 28),
            colour="Black",
            brand="Dell",
            item_name="Laptop bag",
            description="Black bag, grey strap, front scratch, zipper",
            distinguishing_features="",
            verification_answer_hash="must-not-affect-scoring",
        )
        self.found = SimpleNamespace(
            category_id=category_id,
            area="Cafeteria, Block B",
            event_date=date(2026, 10, 29),
            colour="Black",
            brand="Dell",
            item_name="Laptop shoulder bag",
            description="Black bag with grey strap, front button and dent",
            distinguishing_features="",
            verification_answer_hash="another-private-value",
        )

    def test_reference_match_scores_91_and_is_strong(self):
        result = calculate_pair(self.lost, self.found)

        self.assertEqual(result["total_score"], 91)
        self.assertEqual(result["match_level"], MatchLevel.STRONG)
        self.assertEqual(
            [
                result["category_score"],
                result["location_score"],
                result["date_score"],
                result["colour_score"],
                result["brand_score"],
                result["name_score"],
                result["description_score"],
            ],
            [25, 20, 12, 10, 10, 8, 6],
        )

    def test_date_buckets_and_found_before_lost(self):
        lost = date(2026, 10, 1)
        self.assertEqual(date_score(lost, date(2026, 10, 1)), 15)
        self.assertEqual(date_score(lost, date(2026, 10, 3)), 12)
        self.assertEqual(date_score(lost, date(2026, 10, 6)), 8)
        self.assertEqual(date_score(lost, date(2026, 10, 11)), 4)
        self.assertEqual(date_score(lost, date(2026, 10, 12)), 0)
        self.assertEqual(date_score(lost, date(2026, 9, 30)), 0)

    def test_synonyms_and_explanation_do_not_expose_private_answers(self):
        self.assertEqual(tokens("Mobile phone, MOBILE"), {"phone"})
        self.assertEqual(overlap_score("Laptop bag", "Laptop shoulder bag", 10), 8)

        result = calculate_pair(self.lost, self.found)
        explanation = " ".join(result["explanation"]["reasons"])
        self.assertNotIn(self.lost.verification_answer_hash, explanation)
        self.assertNotIn(self.found.verification_answer_hash, explanation)

    def test_category_mismatch_cannot_be_a_strong_match(self):
        self.found.category_id = uuid.uuid4()
        result = calculate_pair(self.lost, self.found)

        self.assertEqual(result["category_score"], 0)
        self.assertNotEqual(result["match_level"], MatchLevel.STRONG)


if __name__ == "__main__":
    unittest.main()
