import contextlib
import io
import json
import os
import unittest
from unittest.mock import Mock, patch

import httpx
from agent import build_agent, main
from guardrails import (
    clean_output,
    contains_pii,
    is_restaurant_related,
    validate_question,
)
from langchain_openai.chat_models.base import OpenAIAuthenticationError
from tools import calculate_dining_cost, get_restaurants, search_restaurants


class RestaurantToolTests(unittest.TestCase):
    def test_authentication_error_is_reported_without_traceback(self) -> None:
        response = httpx.Response(
            401,
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        authentication_error = OpenAIAuthenticationError(
            "Invalid API key",
            response=response,
            body=None,
        )
        agent = Mock()
        agent.invoke.side_effect = authentication_error
        output = io.StringIO()

        with (
            patch("agent.build_agent", return_value=agent),
            patch("builtins.input", side_effect=["Show me Indian restaurants.", "exit"]),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(output),
        ):
            main()

        self.assertIn("OpenAI rejected the API key (401)", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_agent_builds_without_making_an_api_request(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-placeholder"}):
            agent = build_agent()
        self.assertIsNotNone(agent)

    def test_supplied_dataset_is_loaded(self) -> None:
        self.assertEqual(len(get_restaurants()), 240)

    def test_search_matches_cuisine_and_location(self) -> None:
        cuisine_results = json.loads(
            search_restaurants.invoke({"keyword": "Indian"})
        )
        location_results = json.loads(
            search_restaurants.invoke({"keyword": "Hyderabad"})
        )
        self.assertTrue(any(item["name"] == "Spice Garden" for item in cuisine_results))
        self.assertTrue(all(item["location"] == "Hyderabad" for item in location_results))

    def test_dining_cost_and_invalid_inputs(self) -> None:
        result = json.loads(
            calculate_dining_cost.invoke({"restaurant_id": "R101", "guests": 4})
        )
        self.assertEqual(result["estimated_total"], 3200)
        self.assertIn("between 1 and 20", calculate_dining_cost.invoke(
            {"restaurant_id": "R101", "guests": 50}
        ))
        self.assertIn("was not found", calculate_dining_cost.invoke(
            {"restaurant_id": "missing", "guests": 2}
        ))


class GuardrailTests(unittest.TestCase):
    def test_question_validation(self) -> None:
        self.assertIsNotNone(validate_question("  "))
        self.assertIsNotNone(validate_question("x" * 1001))
        self.assertIsNotNone(validate_question("cost for 50 guests"))
        self.assertIsNotNone(validate_question("My email is john@example.com"))
        self.assertIsNone(validate_question("Show me Indian restaurants"))

    def test_domain_and_context_guards(self) -> None:
        self.assertTrue(is_restaurant_related("Show me Indian restaurants"))
        self.assertFalse(is_restaurant_related("What is the largest mammal?"))
        self.assertFalse(is_restaurant_related("6 people"))
        self.assertTrue(is_restaurant_related("6 people", has_context=True))
        self.assertTrue(
            is_restaurant_related(
                "What if I increase it to 6 people?", has_context=True
            )
        )

    def test_pii_detection_and_redaction(self) -> None:
        self.assertTrue(contains_pii("Call me at 9876543210"))
        cleaned = clean_output("Email john@example.com or call 9876543210.")
        self.assertNotIn("john@example.com", cleaned)
        self.assertNotIn("9876543210", cleaned)
        self.assertIn("[EMAIL REDACTED]", cleaned)
        self.assertIn("[PHONE REDACTED]", cleaned)


if __name__ == "__main__":
    unittest.main()
