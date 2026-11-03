import unittest

from fastapi.testclient import TestClient

from app.main import app


class ApplicationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_health_is_available_without_database_access(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")
        self.assertTrue(response.headers.get("X-Request-ID"))

    def test_private_endpoint_requires_a_bearer_token(self):
        response = self.client.get("/api/v1/users/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHENTICATED")
        self.assertEqual(response.json()["error"]["fields"], {})

    def test_request_validation_uses_the_public_error_contract(self):
        response = self.client.post("/api/v1/auth/register", json={"email": "not-an-email"})
        self.assertEqual(response.status_code, 422)
        body = response.json()["error"]
        self.assertEqual(body["code"], "VALIDATION_ERROR")
        self.assertIn("full_name", body["fields"])
        self.assertNotIn("input", response.text)

    def test_login_contract_accepts_json_email_and_password(self):
        operation = app.openapi()["paths"]["/api/v1/auth/login"]["post"]
        content = operation["requestBody"]["content"]
        self.assertIn("application/json", content)

    def test_openapi_contains_core_end_to_end_routes(self):
        paths = app.openapi()["paths"]
        for path in (
            "/api/v1/reports",
            "/api/v1/reports/{report_id}/matches",
            "/api/v1/claims",
            "/api/v1/claims/{claim_id}/complete",
            "/api/v1/dashboard/admin",
            "/api/v1/admin/reports",
        ):
            self.assertIn(path, paths)


if __name__ == "__main__":
    unittest.main()
