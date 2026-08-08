#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: MIT
# See https://github.com/aboutcode-org/django-altcha for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import base64
import datetime
import json
import logging
import warnings

from django import forms
from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import HiddenInput
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.http import require_GET

import altcha

from .conf import get_setting
from .conf import get_workers_urls

__version__ = "1.1.0"
VERSION = __version__

logger = logging.getLogger(__name__)

# Options rendered as attributes of the `<altcha-widget>` element.
# https://altcha.org/docs/v2/widget-integration/
WIDGET_ATTRIBUTES = (
    "auto",
    "challenge",
    "configuration",
    "display",
    "language",
    "name",
    "theme",
    "type",
    "workers",
)

# Options collected into the JSON-encoded `configuration` attribute.
# The `fetch` and `verifyFunction` options are intentionally left out as they
# require a JavaScript function value that cannot be expressed from Python.
WIDGET_CONFIGURATION = (
    "audioChallengeLanguage",
    "barPlacement",
    "codeChallenge",
    "codeChallengeDisplay",
    "credentials",
    "debug",
    "disableAutoFocus",
    "floatingAnchor",
    "floatingOffset",
    "floatingPersist",
    "floatingPlacement",
    "hideFooter",
    "hideLogo",
    "humanInteractionSignature",
    "minDuration",
    "mockError",
    "overlayContent",
    "popoverPlacement",
    "retryOnOutOfMemoryError",
    "serverVerificationFields",
    "serverVerificationTimeZone",
    "setCookie",
    "test",
    "timeout",
    "validationMessage",
    "verifyUrl",
)

# ALTCHA v2 widget options replaced by a single `challenge` option in v3.
# https://github.com/altcha-org/altcha/blob/main/MIGRATION-v2.md
RENAMED_OPTIONS = {
    "challengeurl": "challenge",
    "challengejson": "challenge",
}


def get_hmac_key():
    """Return the HMAC key, raising if not configured."""
    hmac_key = get_setting("ALTCHA_HMAC_KEY")
    if not hmac_key:
        logger.error("ALTCHA_HMAC_KEY setting is not configured")
        raise ImproperlyConfigured("The ALTCHA_HMAC_KEY setting must be provided.")
    return hmac_key


def get_challenge_expire_seconds():
    return get_setting("ALTCHA_CHALLENGE_EXPIRE") // 1000


def get_cache():
    """Return the cache backend used for replay attack protection."""
    return caches[get_setting("ALTCHA_CACHE_ALIAS")]


def is_challenge_used(challenge):
    """Check if a challenge has already been used."""
    return get_cache().get(key=challenge) is not None


def mark_challenge_used(challenge, timeout):
    """Mark a challenge as used by storing it in the cache with a timeout."""
    get_cache().set(key=challenge, value=True, timeout=timeout)


def get_altcha_challenge(algorithm=None, cost=None, expires=None):
    """
    Generate and return an ALTCHA challenge.

    Attributes:
        algorithm (str): Key derivation function to use for the Proof-of-Work.
        cost (int): Algorithm-specific cost, iterations for PBKDF2 and SHA.
        expires (int): Expiration time for the challenge in milliseconds.

    Returns:
        altcha.Challenge: The generated challenge.
    """
    expires = expires or get_setting("ALTCHA_CHALLENGE_EXPIRE")

    return altcha.create_challenge(
        algorithm=algorithm or get_setting("ALTCHA_ALGORITHM"),
        cost=cost if cost is not None else get_setting("ALTCHA_COST"),
        expires_at=datetime.datetime.now() + datetime.timedelta(milliseconds=expires),
        hmac_secret=get_hmac_key(),
    )


def get_js_url():
    """Return the URL of the ALTCHA widget JavaScript module."""
    if get_setting("ALTCHA_STRICT_CSP"):
        return get_setting("ALTCHA_JS_STRICT_CSP_URL")
    return get_setting("ALTCHA_JS_URL")


def get_workers_register_script():
    """
    Return the URL of the worker registration module and its extra attributes.

    The worker URLs are resolved server-side and handed to the module as a JSON
    mapping, so that they stay correct under a hashed staticfiles storage.
    """
    attrs = {"data-altcha-workers": json.dumps(get_workers_urls())}
    return get_setting("ALTCHA_WORKERS_REGISTER_URL"), attrs


class ModuleScript(str):
    """
    A ``forms.Media`` JavaScript entry rendered as an ES module ``<script>``.

    ALTCHA is distributed as an ES module, which the default ``forms.Media``
    rendering, a plain ``<script src="...">``, cannot load.
    """

    def __new__(cls, url, attrs=None):
        instance = super().__new__(cls, url)
        instance.attrs = attrs or {}
        return instance

    def __html__(self):
        extra_attrs = format_html_join("", ' {}="{}"', self.attrs.items())
        return format_html(
            '<script src="{}" type="module"{}></script>', str(self), extra_attrs
        )


class AltchaWidget(HiddenInput):
    template_name = "altcha_widget.html"

    def __init__(self, options=None, *args, **kwargs):
        """Initialize the ALTCHA widget with provided options from the field."""
        self.options = options or {}
        super().__init__(*args, **kwargs)

    @property
    def media(self):
        """
        Return the assets of the widget, for projects relying on ``form.media``
        rather than on the assets included by the widget template.
        """
        # The project loads ALTCHA on its own, typically from a bundler.
        if not get_setting("ALTCHA_INCLUDE_ASSETS"):
            return forms.Media()

        js = [ModuleScript(get_js_url())]

        if get_setting("ALTCHA_INCLUDE_TRANSLATIONS"):
            js.append(ModuleScript(get_setting("ALTCHA_JS_TRANSLATIONS_URL")))

        if not get_setting("ALTCHA_STRICT_CSP"):
            return forms.Media(js=js)

        # The modular build registers no algorithm on its own, the workers have
        # to be declared explicitly. This must happen after the widget module is
        # evaluated, hence the entry being appended last.
        js.append(ModuleScript(*get_workers_register_script()))
        return forms.Media(css={"all": [get_setting("ALTCHA_CSS_URL")]}, js=js)

    def get_context(self, name, value, attrs):
        """Generate the widget context, including ALTCHA assets and challenge."""
        context = super().get_context(name, value, attrs)
        context["include_assets"] = get_setting("ALTCHA_INCLUDE_ASSETS")
        context["strict_csp"] = get_setting("ALTCHA_STRICT_CSP")
        context["js_altcha_url"] = get_js_url()
        context["css_altcha_url"] = get_setting("ALTCHA_CSS_URL")
        context["js_translations_url"] = get_setting("ALTCHA_JS_TRANSLATIONS_URL")
        context["include_translations"] = get_setting("ALTCHA_INCLUDE_TRANSLATIONS")
        workers_register_url, workers_attrs = get_workers_register_script()
        context["js_workers_register_url"] = workers_register_url
        context["workers_attrs"] = workers_attrs
        context["widget"]["altcha_options"] = self.get_altcha_options()
        return context

    def get_altcha_options(self):
        """
        Return the ``<altcha-widget>`` attributes for this widget, with the
        options that are not HTML attributes gathered into ``configuration``.
        """
        options = {
            key: value for key, value in self.options.items() if value is not None
        }

        # If a `challenge` URL is provided, the challenge will be fetched from this
        # URL. This can be a local Django view or an external API endpoint.
        # If not provided, a unique challenge is generated locally in a self-hosted
        # mode and inlined as JSON.
        # Since the challenge must be fresh for each form rendering, it is generated
        # inside `get_context`, not `__init__`.
        if not options.get("challenge"):
            options["challenge"] = get_altcha_challenge().to_dict()

        configuration = options.pop("configuration", None) or {}
        if isinstance(configuration, str):
            configuration = json.loads(configuration)
        configuration = dict(configuration)

        for key in list(options):
            if key not in WIDGET_ATTRIBUTES:
                configuration[key] = options.pop(key)

        if configuration:
            options["configuration"] = configuration

        return self.encode_values(options)

    @staticmethod
    def encode_values(data):
        """Return a shallow copy of `data` where lists and dicts are JSON encoded."""
        encoded = {}
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            encoded[key] = value
        return encoded


class AltchaField(forms.Field):
    widget = AltchaWidget
    default_error_messages = {
        "error": _("Failed to process CAPTCHA token"),
        "invalid": _("Invalid CAPTCHA token."),
        "required": _("ALTCHA CAPTCHA token is missing."),
        "replay": _("Challenge has already been used."),
    }
    # Options supported by the ALTCHA v3 widget, all optional.
    # The HTML attributes are documented at:
    # https://altcha.org/docs/v2/widget-integration/#html-attributes
    # Every other option is passed through the `configuration` attribute:
    # https://altcha.org/docs/v2/widget-integration/#configuration
    default_options = dict.fromkeys(WIDGET_ATTRIBUTES + WIDGET_CONFIGURATION)

    def __init__(self, *args, **kwargs):
        """Initialize the ALTCHA field and pass widget options for rendering."""
        for old_name, new_name in RENAMED_OPTIONS.items():
            if old_name in kwargs:
                warnings.warn(
                    f"The AltchaField {old_name!r} option was removed in ALTCHA v3, "
                    f"use {new_name!r} instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                kwargs.setdefault(new_name, kwargs.pop(old_name))
                kwargs.pop(old_name, None)

        widget_options = {
            key: kwargs.pop(key, self.default_options[key])
            for key in self.default_options
        }
        kwargs["widget"] = self.widget(options=widget_options)
        super().__init__(*args, **kwargs)

    def validate(self, value):
        """Validate the CAPTCHA token and verify its authenticity."""
        if not get_setting("ALTCHA_VERIFICATION_ENABLED"):
            logger.debug(
                "ALTCHA validation skipped: ALTCHA_VERIFICATION_ENABLED is False"
            )
            return

        super().validate(value)

        if not value:
            logger.warning("ALTCHA validation failed: missing token")
            raise forms.ValidationError(
                self.error_messages["required"], code="required"
            )

        try:
            result = altcha.verify_solution(payload=value, hmac_secret=get_hmac_key())
        except Exception:
            logger.exception("ALTCHA validation raised an unexpected exception")
            raise forms.ValidationError(self.error_messages["error"], code="error")

        if not result.verified:
            logger.warning("ALTCHA validation failed: %s", get_failure_reason(result))
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")

        self.replay_attack_protection(payload=value)

    def replay_attack_protection(self, payload):
        """Protect against replay attacks by ensuring each challenge is single-use."""
        try:
            challenge = get_challenge_identifier(payload)
        except Exception:
            logger.exception(
                "ALTCHA payload could not be decoded for replay protection"
            )
            raise forms.ValidationError(self.error_messages["error"], code="error")

        if is_challenge_used(challenge):
            logger.warning("ALTCHA replay attack detected: challenge already used")
            raise forms.ValidationError(self.error_messages["replay"], code="invalid")

        # Mark as used for the same duration as challenge expiration
        mark_challenge_used(challenge, timeout=get_challenge_expire_seconds())


def get_challenge_identifier(payload):
    """
    Return a value uniquely identifying the challenge solved by ``payload``.

    The signature of a challenge is an HMAC over its parameters, which include a
    random nonce and salt, and is therefore unique to a single challenge.
    """
    payload_data = json.loads(base64.b64decode(payload).decode())
    signature = payload_data["challenge"]["signature"]
    if not signature:
        raise ValueError("Missing challenge signature")
    return signature


def get_failure_reason(result):
    """Return a human readable reason for a failed ``VerifySolutionResult``."""
    if getattr(result, "error", None):
        return result.error
    if result.expired:
        return "challenge expired"
    if result.invalid_signature:
        return "invalid challenge signature"
    if result.invalid_solution:
        return "invalid solution"
    return "unknown error"


class AltchaChallengeView(View):
    algorithm = None
    cost = None
    expires = None

    @method_decorator(require_GET)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Use view's class attributes or kwargs
        challenge = get_altcha_challenge(
            algorithm=kwargs.get("algorithm", self.algorithm),
            cost=kwargs.get("cost", self.cost),
            expires=kwargs.get("expires", self.expires),
        )
        logger.debug("ALTCHA challenge issued")
        return JsonResponse(challenge.to_dict())
