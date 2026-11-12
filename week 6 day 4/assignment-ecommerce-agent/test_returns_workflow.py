import asyncio
import io
import json
import os
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import returns_workflow
from returns_workflow import (
    ConfigurationError,
    _build_workflow,
    combine_eligibility_findings,
    deterministic_risk_flags,
    evaluate_policy,
    load_requests,
    manager_decision,
    parse_risk_response,
    run_request,
    validate_customer_draft,
)


class FakeResult:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeAgent:
    async def run(self, prompt: str) -> FakeResult:
        payload = json.loads(prompt)
        if "policy_checks" in payload:
            return FakeResult("The deterministic eligibility checks are listed.")
        if "eligibility_issues" in payload and "request" in payload:
            return FakeResult("LOW | No additional risk beyond the supplied facts.")

        decision = payload["final_decision"]
        if decision == "MANAGER_REJECTED":
            return FakeResult("Your request was not approved. No action was taken.")
        return FakeResult(
            "Your request has been approved for processing. "
            "This is a simulation; no action has been completed."
        )


class ReturnsWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.requests = load_requests(Path(__file__).with_name("returns.json"))
        cls.fake_agent = FakeAgent()

    def test_policy_rules_select_expected_automatic_requests(self) -> None:
        automatically_eligible = []
        for request in self.requests:
            checks = evaluate_policy(request)
            risk_flags = deterministic_risk_flags(request)
            risk_level = "HIGH" if risk_flags else "LOW"
            final_checks, _ = combine_eligibility_findings(
                checks,
                risk_level,
                "No high risk identified." if risk_level == "LOW" else "; ".join(risk_flags),
            )
            if all(check["passed"] for check in final_checks):
                automatically_eligible.append(request["request_id"])

        self.assertEqual(
            automatically_eligible,
            ["RET201", "RET203", "RET208", "RET210"],
        )

    def test_missing_api_configuration_is_reported(self) -> None:
        missing_path = Path(__file__).with_name("missing-config-test.env")
        with (
            patch.object(returns_workflow, "LOCAL_ENV_FILE", missing_path),
            patch.object(returns_workflow, "DEMO_CONFIG_FILE", missing_path),
            patch.dict(os.environ, {}, clear=True),
            self.assertRaisesRegex(ConfigurationError, "AZURE_OPENAI_API_KEY"),
        ):
            returns_workflow.load_settings()

    def test_invalid_risk_response_is_not_silently_accepted(self) -> None:
        with self.assertRaisesRegex(ValueError, "must start"):
            parse_risk_response("Probably low risk")

    def test_manager_decision_validation(self) -> None:
        self.assertEqual(manager_decision(" APPROVE "), "approve")
        with self.assertRaisesRegex(ValueError, "approve.*reject"):
            manager_decision("maybe")

    def test_customer_draft_cannot_claim_a_refund_was_processed(self) -> None:
        with self.assertRaisesRegex(ValueError, "claimed"):
            validate_customer_draft(
                "Your request has been approved. Your refund has already been processed.",
                "AUTO_APPROVED",
            )
        with self.assertRaisesRegex(ValueError, "rejection"):
            validate_customer_draft("Thank you for contacting us.", "MANAGER_REJECTED")

    def test_customer_draft_accepts_equivalent_approval_wording(self) -> None:
        draft = (
            "Your return request is eligible under the policy. "
            "This is a draft only; no refund has been processed."
        )
        self.assertEqual(
            validate_customer_draft(draft, "AUTO_APPROVED"),
            draft,
        )

    def test_all_ten_workflows_resume_and_keep_human_decisions(self) -> None:
        workflow = _build_workflow(
            self.fake_agent,
            self.fake_agent,
            self.fake_agent,
        )
        decisions = {
            "RET204": ["invalid", "approve"],
            "RET205": ["reject"],
        }
        output_text = io.StringIO()
        results: list[dict[str, Any]] = []

        async def run_all() -> None:
            for request in self.requests:
                answers = iter(decisions.get(request["request_id"], ["approve"]))
                result = await run_request(
                    workflow,
                    dict(request),
                    input_fn=lambda _prompt: next(answers),
                    output=output_text,
                )
                results.append(result)

        asyncio.run(run_all())
        self.assertEqual(len(results), 10)
        by_id = {result["request_id"]: result for result in results}
        self.assertEqual(by_id["RET201"]["final_decision"], "AUTO_APPROVED")
        self.assertEqual(by_id["RET204"]["final_decision"], "MANAGER_APPROVED")
        self.assertEqual(by_id["RET205"]["final_decision"], "MANAGER_REJECTED")
        self.assertEqual(by_id["RET204"]["approval_route"], "Human Review")
        self.assertEqual(by_id["RET205"]["approval_route"], "Human Review")
        self.assertIn("Invalid input", output_text.getvalue())
        self.assertEqual(
            sum(result["final_decision"] == "AUTO_APPROVED" for result in results),
            4,
        )
        self.assertTrue(
            all(
                result["simulation_notice"]
                for result in results
            )
        )
        print("Offline graph integration decisions (fake agents, no API calls):")
        for request_id in ("RET201", "RET204", "RET205"):
            result = by_id[request_id]
            print(
                f"{request_id}: {result['approval_route']} -> "
                f"{result['final_decision']}"
            )


if __name__ == "__main__":
    unittest.main()
