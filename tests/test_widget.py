#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: MIT
# See https://github.com/aboutcode-org/django-altcha for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import json

from django.test import TestCase
from django.test import override_settings

from django_altcha import AltchaWidget

JS_URL = "/static/altcha/altcha.min.js"
JS_STRICT_CSP_URL = "/static/altcha/external/altcha.min.js"
CSS_URL = "/static/altcha/external/altcha.css"
WORKERS_REGISTER_URL = "/static/altcha/external/altcha-workers.js"
JS_TRANSLATIONS_URL = "/static/altcha/i18n/all.js"


class DjangoAltchaWidgetTest(TestCase):
    def test_widget_initialization_with_default_options(self):
        widget = AltchaWidget()
        self.assertNotIn("challenge", widget.options)
        self.assertNotIn("auto", widget.options)

    def test_widget_initialization_with_custom_options(self):
        options = {
            "auto": "onload",
            "minDuration": 500,
            "debug": True,
        }
        widget = AltchaWidget(options)
        self.assertEqual(widget.options["auto"], "onload")
        self.assertEqual(widget.options["minDuration"], 500)
        self.assertEqual(widget.options["debug"], True)

    def test_widget_generates_challenge_if_not_provided(self):
        widget = AltchaWidget(options={})  # Pass an empty dictionary
        context = widget.get_context(name="test", value=None, attrs={})
        altcha_options = context["widget"]["altcha_options"]
        challenge = json.loads(altcha_options["challenge"])
        parameters = challenge["parameters"]
        self.assertEqual("PBKDF2/SHA-256", parameters["algorithm"])
        self.assertEqual(5000, parameters["cost"])
        self.assertEqual(32, len(parameters["nonce"]))
        self.assertEqual(32, len(parameters["salt"]))
        self.assertIn("expiresAt", parameters)
        self.assertEqual(64, len(challenge["signature"]))

    def test_widget_challenge_url_is_not_json_encoded(self):
        widget = AltchaWidget(options={"challenge": "/altcha/challenge/"})
        context = widget.get_context(name="test", value=None, attrs={})
        self.assertEqual(
            "/altcha/challenge/", context["widget"]["altcha_options"]["challenge"]
        )

    def test_widget_non_attribute_options_moved_to_configuration(self):
        options = {"auto": "onload", "debug": True, "hideFooter": True}
        widget = AltchaWidget(options)
        altcha_options = widget.get_context("name", None, {})["widget"][
            "altcha_options"
        ]
        self.assertEqual("onload", altcha_options["auto"])
        self.assertNotIn("debug", altcha_options)
        self.assertEqual(
            {"debug": True, "hideFooter": True},
            json.loads(altcha_options["configuration"]),
        )

    def test_widget_explicit_configuration_is_merged(self):
        options = {"configuration": {"timeout": 1000}, "debug": True}
        widget = AltchaWidget(options)
        altcha_options = widget.get_context("name", None, {})["widget"][
            "altcha_options"
        ]
        self.assertEqual(
            {"timeout": 1000, "debug": True},
            json.loads(altcha_options["configuration"]),
        )

    def test_widget_rendering_with_complex_options(self):
        options = {"setCookie": {"name": "altcha", "maxAge": 60}}
        widget = AltchaWidget(options)
        rendered_widget_html = widget.render("name", "value")
        expected = (
            'configuration="{&quot;setCookie&quot;: '
            '{&quot;name&quot;: &quot;altcha&quot;, &quot;maxAge&quot;: 60}}"'
        )
        self.assertIn(expected, rendered_widget_html)

    def test_js_translation_included_if_enabled(self):
        widget = AltchaWidget()

        with override_settings(ALTCHA_INCLUDE_TRANSLATIONS=True):
            rendered_widget_html = widget.render("name", "value")
            self.assertIn(JS_TRANSLATIONS_URL, rendered_widget_html)

        with override_settings(ALTCHA_INCLUDE_TRANSLATIONS=False):
            rendered_widget_html = widget.render("name", "value")
            self.assertNotIn(JS_TRANSLATIONS_URL, rendered_widget_html)

    def test_widget_renders_default_js_url_through_static(self):
        widget = AltchaWidget()
        rendered_html = widget.render("name", "value")
        self.assertIn(JS_URL, rendered_html)

    def test_widget_respects_custom_static_url(self):
        widget = AltchaWidget()
        with override_settings(STATIC_URL="/assets/"):
            rendered_html = widget.render("name", "value")
        self.assertIn("/assets/altcha/altcha.min.js", rendered_html)
        self.assertNotIn(JS_URL, rendered_html)

    def test_widget_resolves_relative_js_url_override(self):
        widget = AltchaWidget()
        with override_settings(ALTCHA_JS_URL="custom/altcha.js"):
            rendered_html = widget.render("name", "value")
        self.assertIn("/static/custom/altcha.js", rendered_html)

    def test_widget_passes_through_absolute_js_url(self):
        widget = AltchaWidget()
        with override_settings(ALTCHA_JS_URL="/my_static/altcha.js"):
            rendered_html = widget.render("name", "value")
        self.assertIn('src="/my_static/altcha.js"', rendered_html)
        self.assertNotIn("/static/my_static/altcha.js", rendered_html)

    def test_widget_passes_through_http_js_url(self):
        widget = AltchaWidget()
        cdn_url = "http://cdn/altcha.min.js"
        with override_settings(ALTCHA_JS_URL=cdn_url):
            rendered_html = widget.render("name", "value")
        self.assertIn(cdn_url, rendered_html)

    def test_widget_passes_through_https_js_url(self):
        widget = AltchaWidget()
        cdn_url = "https://cdn/altcha.min.js"
        with override_settings(ALTCHA_JS_URL=cdn_url):
            rendered_html = widget.render("name", "value")
        self.assertIn(cdn_url, rendered_html)

    def test_widget_resolves_translations_url_through_static(self):
        widget = AltchaWidget()
        with override_settings(
            ALTCHA_INCLUDE_TRANSLATIONS=True,
            STATIC_URL="/assets/",
        ):
            rendered_html = widget.render("name", "value")
        self.assertIn("/assets/altcha/i18n/all.js", rendered_html)

    def test_widget_passes_through_absolute_translations_url(self):
        widget = AltchaWidget()
        cdn_url = "https://cdni18n/all.min.js"
        with override_settings(
            ALTCHA_INCLUDE_TRANSLATIONS=True,
            ALTCHA_JS_TRANSLATIONS_URL=cdn_url,
        ):
            rendered_html = widget.render("name", "value")
        self.assertIn(cdn_url, rendered_html)


class DjangoAltchaWidgetStrictCSPTest(TestCase):
    def test_default_build_is_used_when_strict_csp_is_disabled(self):
        rendered = AltchaWidget().render("name", "value")
        self.assertIn(f'<script async defer src="{JS_URL}" type="module">', rendered)
        self.assertNotIn(JS_STRICT_CSP_URL, rendered)
        self.assertNotIn(CSS_URL, rendered)
        self.assertNotIn(WORKERS_REGISTER_URL, rendered)

    @override_settings(ALTCHA_STRICT_CSP=True)
    def test_strict_csp_switches_to_the_modular_build(self):
        rendered = AltchaWidget().render("name", "value")
        self.assertIn(f'<link rel="stylesheet" href="{CSS_URL}">', rendered)
        self.assertIn(f'<script src="{JS_STRICT_CSP_URL}" type="module">', rendered)
        self.assertIn(f'<script src="{WORKERS_REGISTER_URL}" type="module">', rendered)
        # No `async`: module scripts must be evaluated in document order so that
        # the workers are registered after the widget module is loaded.
        self.assertNotIn("async", rendered)
        self.assertNotIn(f'"{JS_URL}"', rendered)

    @override_settings(ALTCHA_STRICT_CSP=True)
    def test_strict_csp_assets_resolve_through_static_url(self):
        with override_settings(STATIC_URL="/assets/"):
            rendered = AltchaWidget().render("name", "value")

        self.assertIn('href="/assets/altcha/external/altcha.css"', rendered)
        self.assertIn('src="/assets/altcha/external/altcha.min.js"', rendered)
        self.assertIn('src="/assets/altcha/external/altcha-workers.js"', rendered)

    @override_settings(ALTCHA_STRICT_CSP=True)
    def test_strict_csp_workers_url_setting(self):
        rendered = AltchaWidget().render("name", "value")
        self.assertNotIn("data-altcha-workers-url", rendered)

        with override_settings(ALTCHA_WORKERS_URL="https://cdn/workers/"):
            rendered = AltchaWidget().render("name", "value")
        self.assertIn('data-altcha-workers-url="https://cdn/workers/"', rendered)

        # A relative path is resolved through STATIC_URL
        with override_settings(ALTCHA_WORKERS_URL="altcha/workers/"):
            rendered = AltchaWidget().render("name", "value")
        self.assertIn('data-altcha-workers-url="/static/altcha/workers/"', rendered)

    @override_settings(ALTCHA_STRICT_CSP=True)
    def test_strict_csp_js_url_override(self):
        # ALTCHA_JS_URL points at the default build and is ignored in strict mode
        with override_settings(ALTCHA_JS_URL="https://cdn/altcha.min.js"):
            rendered = AltchaWidget().render("name", "value")
        self.assertIn(JS_STRICT_CSP_URL, rendered)
        self.assertNotIn("https://cdn/altcha.min.js", rendered)

        with override_settings(ALTCHA_JS_STRICT_CSP_URL="https://cdn/external.js"):
            rendered = AltchaWidget().render("name", "value")
        self.assertIn('src="https://cdn/external.js"', rendered)
        self.assertNotIn(JS_STRICT_CSP_URL, rendered)


class DjangoAltchaWidgetMediaTest(TestCase):
    def test_media_default_build(self):
        media = AltchaWidget().media
        self.assertEqual(
            [f'<script src="{JS_URL}" type="module"></script>'], media.render_js()
        )
        self.assertEqual([], list(media.render_css()))

    def test_media_includes_translations_when_enabled(self):
        with override_settings(ALTCHA_INCLUDE_TRANSLATIONS=True):
            media = AltchaWidget().media

        self.assertEqual(
            [
                f'<script src="{JS_URL}" type="module"></script>',
                f'<script src="{JS_TRANSLATIONS_URL}" type="module"></script>',
            ],
            media.render_js(),
        )

    @override_settings(ALTCHA_STRICT_CSP=True)
    def test_media_strict_csp(self):
        media = AltchaWidget().media
        self.assertEqual(
            [
                f'<script src="{JS_STRICT_CSP_URL}" type="module"></script>',
                f'<script src="{WORKERS_REGISTER_URL}" type="module"></script>',
            ],
            media.render_js(),
        )
        self.assertEqual(
            [f'<link href="{CSS_URL}" media="all" rel="stylesheet">'],
            list(media.render_css()),
        )

    @override_settings(ALTCHA_STRICT_CSP=True)
    def test_media_strict_csp_with_workers_url(self):
        with override_settings(ALTCHA_WORKERS_URL="/assets/workers/"):
            media = AltchaWidget().media

        self.assertIn(
            f'<script src="{WORKERS_REGISTER_URL}" type="module"'
            ' data-altcha-workers-url="/assets/workers/"></script>',
            media.render_js(),
        )
