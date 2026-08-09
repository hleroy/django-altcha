from datetime import datetime
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test import override_settings

from django_altcha_widget import get_altcha_challenge
from django_altcha_widget import get_hmac_key


class DjangoAltchaUtilsTest(TestCase):
    def test_get_hmac_key(self):
        self.assertEqual("altcha-insecure-hmac-0123456789abcdef", get_hmac_key())

        with override_settings(ALTCHA_HMAC_KEY=None):
            with self.assertRaises(ImproperlyConfigured):
                get_hmac_key()

    def test_get_altcha_challenge_algorithm_and_cost(self):
        # Default ALTCHA_ALGORITHM and ALTCHA_COST are applied
        challenge = get_altcha_challenge()
        self.assertEqual("PBKDF2/SHA-256", challenge.parameters.algorithm)
        self.assertEqual(5000, challenge.parameters.cost)

        # Provided arguments are applied
        challenge = get_altcha_challenge(algorithm="SHA-256", cost=50)
        self.assertEqual("SHA-256", challenge.parameters.algorithm)
        self.assertEqual(50, challenge.parameters.cost)

        # Custom settings are applied
        with override_settings(ALTCHA_ALGORITHM="SCRYPT", ALTCHA_COST=1024):
            challenge = get_altcha_challenge()
            self.assertEqual("SCRYPT", challenge.parameters.algorithm)
            self.assertEqual(1024, challenge.parameters.cost)

    def test_get_altcha_challenge_is_signed(self):
        challenge = get_altcha_challenge()
        self.assertEqual(64, len(challenge.signature))
        # Each challenge is unique
        self.assertNotEqual(challenge.signature, get_altcha_challenge().signature)

    def assertExpiresIn(self, challenge, milliseconds):
        """Assert the challenge expires `milliseconds` from now, within a second."""
        expected = datetime.now() + timedelta(milliseconds=milliseconds)
        self.assertAlmostEqual(
            expected.timestamp(), challenge.parameters.expires_at, delta=1
        )

    def test_get_altcha_challenge_expire(self):
        # Default ALTCHA_CHALLENGE_EXPIRE is applied
        self.assertExpiresIn(get_altcha_challenge(), 1200000)

        # Provided `expires` argument is applied
        self.assertExpiresIn(get_altcha_challenge(expires=10000), 10000)

        # Custom ALTCHA_CHALLENGE_EXPIRE value is applied
        with override_settings(ALTCHA_CHALLENGE_EXPIRE=9999):
            self.assertExpiresIn(get_altcha_challenge(), 9999)
