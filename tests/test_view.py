from django.test import TestCase
from django.test import override_settings
from django.urls import reverse


class DjangoAltchaViewTest(TestCase):
    def test_challenge_view_returns_200(self):
        response = self.client.get(reverse("altcha_challenge"))
        self.assertEqual(response.status_code, 200)

    def test_challenge_view_returns_json(self):
        response = self.client.get(reverse("altcha_challenge"))
        self.assertEqual(response["Content-Type"], "application/json")

    def test_challenge_response_contains_expected_keys(self):
        response = self.client.get(reverse("altcha_challenge"))
        data = response.json()

        self.assertEqual(["parameters", "signature"], list(data.keys()))

        expected_keys = [
            "algorithm",
            "cost",
            "keyLength",
            "keyPrefix",
            "nonce",
            "salt",
            "expiresAt",
        ]
        parameters = data["parameters"]
        self.assertEqual(expected_keys, list(parameters.keys()))

        self.assertEqual("PBKDF2/SHA-256", parameters["algorithm"])
        # The `cost` view attribute is applied
        self.assertEqual(100, parameters["cost"])

    def test_challenge_view_algorithm_and_cost_settings(self):
        with override_settings(ALTCHA_ALGORITHM="SHA-512", ALTCHA_COST=42):
            response = self.client.get(reverse("altcha_challenge_defaults"))

        parameters = response.json()["parameters"]
        self.assertEqual("SHA-512", parameters["algorithm"])
        self.assertEqual(42, parameters["cost"])
