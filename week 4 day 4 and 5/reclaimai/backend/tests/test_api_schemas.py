import unittest
import uuid
from datetime import date, datetime, timezone

from pydantic import ValidationError

from app.core.security import hash_verification_answer, verify_verification_answer
from app.models.enums import ReportType
from app.schemas.claim import ClaimReview
from app.schemas.report import PublicReportResponse, ReportCreate, ReportUpdate
from app.services.idempotency_service import request_fingerprint


class ApiSchemaTests(unittest.TestCase):
    def valid_report(self, report_type=ReportType.LOST):
        body = {
            "report_type": report_type.value,
            "category_id": str(uuid.uuid4()),
            "item_name": "Leather wallet",
            "colour": "Brown",
            "event_date": date.today().isoformat(),
            "area": "Main library",
            "description": "Small brown wallet with a stitched edge.",
        }
        if report_type == ReportType.FOUND:
            body.update(
                verification_question="What is the card holder colour?",
                verification_answer="  Blue   ",
            )
        return body

    def test_found_report_requires_private_verification_fields(self):
        with self.assertRaises(ValidationError):
            ReportCreate.model_validate(self.valid_report(ReportType.FOUND) | {
                "verification_question": "",
                "verification_answer": "",
            })

        report = ReportCreate.model_validate(self.valid_report(ReportType.FOUND))
        self.assertEqual(report.verification_answer, "Blue")

    def test_reports_reject_future_dates_and_unknown_fields(self):
        invalid_date = self.valid_report()
        invalid_date["event_date"] = date.today().replace(year=date.today().year + 1).isoformat()
        with self.assertRaises(ValidationError):
            ReportCreate.model_validate(invalid_date)

        with self.assertRaises(ValidationError):
            ReportCreate.model_validate(self.valid_report() | {"unexpected": "field"})

    def test_report_patch_rejects_null_required_values(self):
        with self.assertRaises(ValidationError):
            ReportUpdate.model_validate({"description": None})

    def test_public_projection_omits_private_report_fields(self):
        report = PublicReportResponse.model_validate({
            "id": uuid.uuid4(),
            "reference": "RA-123456",
            "report_type": "FOUND",
            "category_id": uuid.uuid4(),
            "item_name": "Umbrella",
            "colour": "Blue",
            "brand": None,
            "event_date": date.today(),
            "area": "Main hall",
            "description": "Blue umbrella with a curved handle.",
            "distinguishing_features": None,
            "image_url": None,
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc),
            "verification_question": "Hidden question",
            "verification_answer_hash": "hidden hash",
            "location_details": "hidden location",
            "storage_instructions": "hidden storage",
        })
        payload = report.model_dump()
        self.assertNotIn("verification_question", payload)
        self.assertNotIn("verification_answer_hash", payload)
        self.assertNotIn("location_details", payload)
        self.assertNotIn("storage_instructions", payload)

    def test_idempotency_fingerprint_is_stable_and_content_sensitive(self):
        first = {"item_name": "Laptop bag", "category_id": "category"}
        equivalent = {"category_id": "category", "item_name": "Laptop bag"}
        changed = {"item_name": "Different bag", "category_id": "category"}
        self.assertEqual(request_fingerprint(first), request_fingerprint(equivalent))
        self.assertNotEqual(request_fingerprint(first), request_fingerprint(changed))

    def test_verification_answers_ignore_case_and_repeated_whitespace(self):
        stored = hash_verification_answer(" Blue notebook ")
        self.assertTrue(verify_verification_answer("blue   notebook", stored))
        self.assertFalse(verify_verification_answer("red notebook", stored))

    def test_claim_decision_requires_a_review_note(self):
        with self.assertRaises(ValidationError):
            ClaimReview.model_validate({"status": "APPROVED", "review_comment": "  "})
        review = ClaimReview.model_validate({"status": "UNDER_REVIEW"})
        self.assertIsNone(review.review_comment)


if __name__ == "__main__":
    unittest.main()
