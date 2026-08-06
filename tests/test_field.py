#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: MIT
# See https://github.com/aboutcode-org/django-altcha for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import base64
import json
from unittest import mock

from django import forms
from django.forms import ValidationError
from django.test import TestCase
from django.test import override_settings

import altcha

from django_altcha import AltchaField
from django_altcha import AltchaWidget
from django_altcha import get_altcha_challenge
from django_altcha import is_challenge_used

TEST_CHALLENGE = "test-challenge-123"


def make_valid_payload(signature=TEST_CHALLENGE):
    """Return a base64-encoded ALTCHA v2 payload skeleton."""
    payload_dict = {
        "challenge": {"parameters": {}, "signature": signature},
        "solution": {"counter": 1, "derivedKey": "00"},
    }
    json_str = json.dumps(payload_dict)
    encoded_bytes = base64.b64encode(json_str.encode("utf-8"))
    return encoded_bytes.decode("utf-8")


class DjangoAltchaFieldTest(TestCase):
    def setUp(self):
        class TestForm(forms.Form):
            altcha_field = AltchaField()

        self.form_class = TestForm

    def test_altcha_field_renders_widget(self):
        form = self.form_class()
        self.assertIsInstance(form.fields["altcha_field"].widget, AltchaWidget)

    def test_altcha_field_options_to_widget(self):
        altcha_field = AltchaField(display="floating", timeout=10000)
        self.assertEqual("floating", altcha_field.widget.options["display"])
        self.assertEqual(10000, altcha_field.widget.options["timeout"])

    def test_altcha_field_unknown_option_is_rejected(self):
        # `maxnumber` and `floating` are ALTCHA v2 options, removed in v3.
        with self.assertRaises(TypeError):
            AltchaField(maxnumber=50)
        with self.assertRaises(TypeError):
            AltchaField(floating=True)

    def test_altcha_field_deprecated_challenge_options(self):
        with self.assertWarns(DeprecationWarning):
            altcha_field = AltchaField(challengeurl="/altcha/challenge/")
        self.assertEqual("/altcha/challenge/", altcha_field.widget.options["challenge"])

        with self.assertWarns(DeprecationWarning):
            altcha_field = AltchaField(challengejson='{"parameters": {}}')
        self.assertEqual('{"parameters": {}}', altcha_field.widget.options["challenge"])

    def test_altcha_field_validate_verification_enabled_setting(self):
        altcha_field = AltchaField()
        with self.assertRaises(ValidationError):
            altcha_field.validate("a_value")

        with override_settings(ALTCHA_VERIFICATION_ENABLED=False):
            self.assertIsNone(altcha_field.validate("a_value"))

    def test_altcha_field_with_missing_value_raises_required_error(self):
        form = self.form_class(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("altcha_field", form.errors)
        self.assertEqual(
            form.errors["altcha_field"][0], "ALTCHA CAPTCHA token is missing."
        )

    @mock.patch("altcha.verify_solution")
    def test_altcha_field_validation_calls_verify_solution(self, mock_verify_solution):
        self.assertFalse(is_challenge_used(TEST_CHALLENGE))
        mock_verify_solution.return_value = mock.Mock(verified=True)
        valid_payload = make_valid_payload()
        form = self.form_class(data={"altcha_field": valid_payload})
        self.assertTrue(form.is_valid())
        mock_verify_solution.assert_called_once_with(
            payload=valid_payload,
            hmac_secret=mock.ANY,
        )

        # Replay the validation using the same challenge
        self.assertTrue(is_challenge_used(TEST_CHALLENGE))
        form = self.form_class(data={"altcha_field": valid_payload})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["altcha_field"][0], "Challenge has already been used."
        )

    @mock.patch("altcha.verify_solution")
    def test_altcha_field_validation_fails_on_invalid_token(self, mock_verify_solution):
        mock_verify_solution.return_value = mock.Mock(
            verified=False, error="Invalid altcha payload"
        )
        form = self.form_class(data={"altcha_field": "invalid_token"})
        self.assertFalse(form.is_valid())
        self.assertIn("altcha_field", form.errors)
        self.assertEqual(form.errors["altcha_field"][0], "Invalid CAPTCHA token.")

    @mock.patch("altcha.verify_solution")
    def test_altcha_field_validation_handles_exception(self, mock_verify_solution):
        mock_verify_solution.side_effect = Exception("Verification failed")
        form = self.form_class(data={"altcha_field": "some_token"})
        self.assertFalse(form.is_valid())
        self.assertIn("altcha_field", form.errors)
        self.assertEqual(
            form.errors["altcha_field"][0], "Failed to process CAPTCHA token"
        )

    def test_altcha_field_validation_with_a_solved_challenge(self):
        """Solve a real challenge and validate the resulting payload end to end."""
        challenge = get_altcha_challenge(algorithm="PBKDF2/SHA-256", cost=100)
        solution = altcha.solve_challenge(challenge)
        payload = altcha.Payload(challenge, solution).to_base64()

        form = self.form_class(data={"altcha_field": payload})
        self.assertTrue(form.is_valid(), form.errors)

        # The very same payload cannot be submitted twice
        form = self.form_class(data={"altcha_field": payload})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["altcha_field"][0], "Challenge has already been used."
        )

    def test_altcha_field_validation_with_a_tampered_challenge(self):
        challenge = get_altcha_challenge(algorithm="PBKDF2/SHA-256", cost=100)
        solution = altcha.solve_challenge(challenge)
        payload_data = altcha.Payload(challenge, solution).to_dict()
        payload_data["challenge"]["parameters"]["cost"] = 1
        payload = base64.b64encode(json.dumps(payload_data).encode()).decode()

        form = self.form_class(data={"altcha_field": payload})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["altcha_field"][0], "Invalid CAPTCHA token.")

    def test_altcha_field_validation_with_an_expired_challenge(self):
        with override_settings(ALTCHA_CHALLENGE_EXPIRE=-1000):
            challenge = get_altcha_challenge(algorithm="PBKDF2/SHA-256", cost=100)
        solution = altcha.solve_challenge(challenge)
        payload = altcha.Payload(challenge, solution).to_base64()

        form = self.form_class(data={"altcha_field": payload})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["altcha_field"][0], "Invalid CAPTCHA token.")

    def test_altcha_field_validation_with_a_test_mode_payload(self):
        # The widget emits this payload when the `test` option is enabled.
        payload_data = {"challenge": None, "solution": None, "test": True}
        payload = base64.b64encode(json.dumps(payload_data).encode()).decode()

        form = self.form_class(data={"altcha_field": payload})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["altcha_field"][0], "Invalid CAPTCHA token.")
