#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: MIT
# See https://github.com/aboutcode-org/django-altcha for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

"""
Lazy settings access for django-altcha.

Django settings read at module import time can capture stale or default
values if the module is imported before settings are fully configured.
This module avoids that by deferring all reads to call time through
django.conf.settings, which is a lazy object guaranteed to reflect the
final project configuration.
"""

from django.conf import settings
from django.templatetags.static import static

_DEFAULTS = {
    # Set to `False` to skip Altcha validation altogether.
    "ALTCHA_VERIFICATION_ENABLED": True,
    # This key is used to HMAC-sign ALTCHA challenges and must be kept secret.
    "ALTCHA_HMAC_KEY": None,
    # URL of the Altcha JavaScript file.
    # Defaults to the bundled django-altcha file, resolved through STATIC_URL.
    # Accepts:
    #  - a relative static path (e.g. "altcha/altcha.min.js"),
    #  - an absolute path starting with "/",
    #  - or a fully-qualified URL (http:// or https://) for CDN usage.
    # Relative paths are passed through Django's staticfiles storage,
    # so they work with STATIC_URL customization and ManifestStaticFilesStorage.
    "ALTCHA_JS_URL": "altcha/altcha.min.js",
    # URL of the Altcha translations JavaScript file.
    # Same resolution rules as ALTCHA_JS_URL above.
    "ALTCHA_JS_TRANSLATIONS_URL": "altcha/i18n/all.js",
    # Whether to include Altcha translations.
    # https://altcha.org/docs/v2/widget-integration/#internationalization-i18n
    "ALTCHA_INCLUDE_TRANSLATIONS": False,
    # Key derivation function used for the Proof-of-Work challenges.
    # Supported: "PBKDF2/SHA-256", "PBKDF2/SHA-384", "PBKDF2/SHA-512",
    # "SHA-256", "SHA-384", "SHA-512", "ARGON2ID", "SCRYPT".
    # https://altcha.org/docs/v2/proof-of-work-captcha/
    "ALTCHA_ALGORITHM": "PBKDF2/SHA-256",
    # Algorithm-specific cost: iterations for PBKDF2 and SHA, time cost for
    # ARGON2ID and SCRYPT. 5000 is the value recommended upstream for
    # PBKDF2/SHA-256.
    "ALTCHA_COST": 5000,
    # Serve the modular Altcha build, for projects enforcing a strict
    # Content-Security-Policy (no inline styles, no `blob:` workers).
    # https://altcha.org/docs/v2/content-security-policy-csp/
    "ALTCHA_STRICT_CSP": False,
    # URL of the modular Altcha JavaScript file, used in place of ALTCHA_JS_URL
    # when ALTCHA_STRICT_CSP is enabled.
    # Same resolution rules as ALTCHA_JS_URL above.
    "ALTCHA_JS_STRICT_CSP_URL": "altcha/external/altcha.min.js",
    # URL of the Altcha stylesheet, only used when ALTCHA_STRICT_CSP is enabled.
    # The default build inlines its own styles and ignores this setting.
    # Same resolution rules as ALTCHA_JS_URL above.
    "ALTCHA_CSS_URL": "altcha/external/altcha.css",
    # URL of the script registering the Proof-of-Work workers, only used when
    # ALTCHA_STRICT_CSP is enabled.
    # Same resolution rules as ALTCHA_JS_URL above.
    "ALTCHA_WORKERS_REGISTER_URL": "altcha/external/altcha-workers.js",
    # URL of the directory containing the Proof-of-Work worker scripts, only
    # used when ALTCHA_STRICT_CSP is enabled.
    # Defaults to `None`, in which case the registration script locates the
    # workers relative to its own URL.
    # Same resolution rules as ALTCHA_JS_URL above.
    "ALTCHA_WORKERS_URL": None,
    # Challenge expiration duration in milliseconds.
    # Default to 20 minutes as per Altcha security recommendations.
    # https://altcha.org/docs/v2/security-recommendations/
    "ALTCHA_CHALLENGE_EXPIRE": 1200000,
    # Django cache alias used to store challenge data for replay attack protection.
    # Defaults to the "default" cache backend.
    # https://docs.djangoproject.com/en/dev/ref/settings/#caches
    "ALTCHA_CACHE_ALIAS": "default",
}

# Settings whose value is a static asset path that should be resolved through
# Django's staticfiles machinery when given as a relative path.
_STATIC_ASSET_SETTINGS = {
    "ALTCHA_JS_URL",
    "ALTCHA_JS_TRANSLATIONS_URL",
    "ALTCHA_JS_STRICT_CSP_URL",
    "ALTCHA_CSS_URL",
    "ALTCHA_WORKERS_REGISTER_URL",
    "ALTCHA_WORKERS_URL",
}


def _is_absolute(path):
    """Return True if `path` is a full URL or an absolute server path."""
    return path.startswith(("http://", "https://", "/"))


def get_setting(name):
    """Look up a django-altcha setting, falling back to the default."""
    if name not in _DEFAULTS:
        raise ValueError(f"Unknown django-altcha setting: {name}")
    value = getattr(settings, name, _DEFAULTS[name])

    # Resolve relative static paths through STATIC_URL so they respect the
    # project's staticfiles configuration and storage backend. Absolute paths
    # and full URLs are passed through untouched, matching the convention
    # used by Django's form Media class.
    if name in _STATIC_ASSET_SETTINGS and value and not _is_absolute(value):
        return static(value)

    return value
