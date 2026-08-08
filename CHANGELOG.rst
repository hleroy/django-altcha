Changelog
=========

v1.1.0 (unreleased)
-------------------

**WARNING Breaking changes:**

1. The bundled JS widget is upgraded to ALTCHA v3.2.1, and the server side moves
   from the v1 Proof-of-Work API to the v2 one. The ``altcha`` requirement is
   raised to ``>=2.1.0,<3.0.0``.
   ALTCHA v3 replaces the v1 hash-matching Proof-of-Work by a key derivation
   function (KDF) based one. Challenges and payloads are not compatible across
   versions: any challenge issued by a previous release is rejected after the
   upgrade. In-flight form submissions will fail validation once and succeed on
   retry.

2. The ``AltchaField`` options are the ALTCHA v3 ones.
   ``challengeurl`` and ``challengejson`` are replaced by a single ``challenge``
   option, and are still accepted with a ``DeprecationWarning``.
   Every other removed option—``floating``, ``overlay``, ``hidefooter``,
   ``hidelogo``, ``maxnumber``, ``strings``, ``delay``, ``mockerror``,
   ``disableautofocus``, ``refetchonexpire``, ``customfetch``, ``credentials``,
   ``workerurl``, ``obfuscated``, ``id``, ``floatinganchor``, ``floatingoffset``,
   ``floatingpersist``, ``overlaycontent``—raises a ``TypeError``.
   Options that the widget does not accept as an HTML attribute are now
   collected into the JSON-encoded ``configuration`` attribute.
   https://github.com/altcha-org/altcha/blob/main/MIGRATION-v2.md

3. ``get_altcha_challenge()`` takes ``algorithm`` and ``cost`` arguments in place
   of ``max_number``, and returns an ``altcha.Challenge`` whose JSON
   representation is obtained with ``to_dict()`` rather than ``__dict__``.
   ``AltchaChallengeView`` accordingly exposes ``algorithm`` and ``cost``
   attributes in place of ``max_number``.

4. The bundled translations moved from ``static/altcha/dist_i18n/all.min.js`` to
   ``static/altcha/i18n/all.js``, following the upstream v3 layout.
   ALTCHA v3 does not publish a minified build of the combined translations.
   Projects setting ``ALTCHA_JS_TRANSLATIONS_URL`` are not affected.

- Upgrade the bundled JS library to the ALTCHA v3.2.1 release.
  Move to the altcha-lib-py v2 API, released in v2.1.0.

- Add a ``ALTCHA_STRICT_CSP`` setting, default to ``False``.
  When enabled, the widget serves the modular ALTCHA build: the stylesheet is
  served as a separate file and the Proof-of-Work workers are loaded from the
  static files rather than from a ``blob:`` URL. This removes the need for
  ``style-src 'unsafe-inline'`` and ``worker-src blob:`` in the
  Content-Security-Policy.
  https://altcha.org/docs/v2/content-security-policy-csp/

- Add ``ALTCHA_JS_STRICT_CSP_URL``, ``ALTCHA_CSS_URL`` and
  ``ALTCHA_WORKERS_REGISTER_URL`` settings, only used in strict CSP mode. They
  follow the same resolution rules as ``ALTCHA_JS_URL``: relative paths go
  through ``STATIC_URL``, absolute paths and full URLs are used as-is.
  ``ALTCHA_WORKERS_URL`` is also added, see below for its resolution rules.

- Add ``ALTCHA_ALGORITHM`` and ``ALTCHA_COST`` settings, defaulting to
  ``"PBKDF2/SHA-256"`` and ``5000``.
  The ``ARGON2ID`` algorithm requires the ``argon2-cffi`` package, available
  through the new ``argon2`` extra.

- Add a ``media`` property on ``AltchaWidget``, so the widget assets can be
  included through ``{{ form.media }}`` instead of the widget template.

- Replay attack protection now keys the cache on the challenge signature, the
  ALTCHA v3 payload no longer carries a ``challenge`` string.

- Add a ``ALTCHA_INCLUDE_ASSETS`` setting, default to ``True``.
  Set it to ``False`` when the project loads ALTCHA on its own, for instance
  when bundling the ``altcha`` npm package with webpack or Vite: the widget then
  emits no ``<script>`` or ``<link>`` tag and its ``media`` is empty, while the
  ``<altcha-widget>`` element and its challenge are still rendered.

- Bundle one translation file per language in addition to the combined
  ``altcha/i18n/all.js``. Pointing ``ALTCHA_JS_TRANSLATIONS_URL`` at a single
  language, e.g. ``"altcha/i18n/fr-fr.js"``, costs 1.4 KB gzipped instead of
  18.2 KB for the combined bundle.

- Pin the vendored ALTCHA version in ``package.json`` and add a Dependabot
  configuration, so that widget upgrades are proposed automatically.
  ``make sync-altcha`` re-vendors the pinned version, verifying every file
  against the matching upstream git tag, and ``make check-altcha`` fails in CI
  when the vendored assets drift from the pin.

- Resolve the Proof-of-Work worker URLs one by one rather than passing a
  directory to the registration script, so that hashed staticfiles storages such
  as ``ManifestStaticFilesStorage`` produce usable URLs.
  ``ALTCHA_WORKERS_URL`` is now used as a plain prefix and is no longer resolved
  through ``STATIC_URL``: it takes an absolute path or a full URL.

v1.0.0 (2026-04-21)
-------------------

- feat: add logging for validation failures and misconfiguration
  https://github.com/aboutcode-org/django-altcha/pull/46

- fix(settings): resolve static asset URLs through STATIC_URL
  https://github.com/aboutcode-org/django-altcha/pull/45

- fix(deps): cap altcha at <2.0.0 for incompatible v2 release
  https://github.com/aboutcode-org/django-altcha/pull/44

v0.10.0 (2026-03-10)
-------------------

**WARNING Breaking changes:**

1. ALTCHA_HMAC_KEY is now mandatory.
  If it's not set in your Django settings, the app will raise ImproperlyConfigured at
  the first challenge creation or validation, instead of silently generating a random
  fallback key.

2. ALTCHA_CACHE_ALIAS now defaults to "default" instead of using a dedicated LocMemCache
  instance. This means ALTCHA automatically benefits from whatever cache backend your
  project already has configured.
  Projects that explicitly set ALTCHA_CACHE_ALIAS are not affected.
  Removed the internal LocMemCache fallback. Cache configuration is now fully handled
  through Django's CACHES setting.

- Refactor the cache configuration using "default" when not provided.
  https://github.com/aboutcode-org/django-altcha/pull/36

- Make the ALTCHA_HMAC_KEY setting mandatory.
  https://github.com/aboutcode-org/django-altcha/pull/35

- Refactor the ALTCHA_* settings loading.
  https://github.com/aboutcode-org/django-altcha/pull/34

v0.9.1 (2026-03-05)
-------------------

- fix: replace altcha.i18n.js bundle by proper dist_i18n/all.js
  https://github.com/aboutcode-org/django-altcha/issues/28

v0.9.0 (2026-01-05)
-------------------

- Upgrade bundled JS library to latest ALTCHA v2.3.0 release.
  Upgrade altcha-lib-py to v1.0.0 release.
  https://github.com/aboutcode-org/django-altcha/pull/25

- Add support for ALTCHA translations.
  https://github.com/aboutcode-org/django-altcha/pull/23

- Add replay attack protection documentation.
  https://github.com/aboutcode-org/django-altcha/pull/26

v0.4.0 (2025-10-21)
-------------------

- Upgrade bundled JS library to latest ALTCHA v2.2.4 release.
  https://github.com/aboutcode-org/django-altcha/pull/20

- Add support for Python 3.14
  https://github.com/aboutcode-org/django-altcha/pull/21

- Add support for providing dict values to AltchaWidget.
  https://github.com/aboutcode-org/django-altcha/pull/20

v0.3.0 (2025-07-25)
-------------------

- Add the ``ALTCHA_HMAC_KEY`` setup as part of the installation.
  A DeprecationWarning is raised when the ``ALTCHA_HMAC_KEY`` is not explicitly defined.
  Providing the ``ALTCHA_HMAC_KEY`` will be mandatory in future release.
  https://github.com/aboutcode-org/django-altcha/issues/15

- Add a ``ALTCHA_VERIFICATION_ENABLED`` setting, default to ``True``.
  This setting, when set to ``False``, allows to skip Altcha validation altogether.

v0.2.0 (2025-06-17)
-------------------

Special thanks to Alex Vandiver alexmv@zulip.com for reporting these issues.

**Important Security Note:**
If you have previously set and used a static ``ALTCHA_HMAC_KEY``,
you **must rotate this key** as part of upgrading to this release.

Earlier versions of ``django-altcha`` accepted challenges that were generated without
an expiration (``expires``) value.
This allowed older challenges to remain valid indefinitely.
As a result, any attacker with access to an old challenge could reuse it to bypass
CAPTCHA validation.

To fully benefit from the security improvements in this release,
you must also **invalidate any existing challenges** by rotating the HMAC key used
to generate and verify them.

- Add a AltchaChallengeView to allow  `challengeurl` a setup.
  This view returns a challenge as JSON to be fetched by the Altcha JS widget.
  https://github.com/aboutcode-org/django-altcha/pull/9

- Add challenge expiration support.
  Default to 20 minutes as per Altcha security recommendations.
  Can be customized through the `ALTCHA_CHALLENGE_EXPIRE` setting.
  https://altcha.org/docs/v2/security-recommendations/
  https://github.com/aboutcode-org/django-altcha/pull/7

- Add protection against replay attacks.
  Verified challenges are now marked as used and cannot be reused,
  helping to prevent repeated or spoofed submissions.
  https://github.com/aboutcode-org/django-altcha/issues/10

v0.1.3 (2025-04-15)
-------------------

- Use the value from the AltchaField `maxnumber` option, when provided, to generate the
  challenge in `get_altcha_challenge`.
  https://github.com/aboutcode-org/django-altcha/issues/5

v0.1.2 (2025-03-31)
-------------------

- Add missing templates/ and static/ directories in the distribution builds.

v0.1.1 (2025-03-31)
-------------------

- Add unit tests.

v0.1.0 (2025-03-31)
-------------------

- Initial release.
