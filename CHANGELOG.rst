Changelog
=========

v1.0.0 (unreleased)
-------------------

First release of ``django-altcha-widget``, a Django form field and widget for
the ALTCHA proof-of-work CAPTCHA.

The project began as a fork of `django-altcha
<https://github.com/aboutcode-org/django-altcha>`_ and is released under the
same MIT License, but it is published as a separate package and shares no
release history with it. Installing both in the same environment is not
supported.

Features
~~~~~~~~

- ``AltchaField`` and ``AltchaWidget`` for Django forms, self-hosted by default:
  the challenge is generated locally and inlined into the rendered HTML, with no
  request to an external service.

- Bundled ALTCHA v3.2.1 widget, so ``pip install django-altcha-widget`` requires
  no JavaScript toolchain. Assets are vendored under
  ``django_altcha_widget/static/altcha/`` and their provenance is recorded in
  ``VENDOR.json``.

- Proof-of-work challenges built on the KDF-based ALTCHA v2 scheme, through the
  ``altcha`` library. ``ALTCHA_ALGORITHM`` and ``ALTCHA_COST`` select the key
  derivation function and its cost, defaulting to ``"PBKDF2/SHA-256"`` and
  ``5000``. ``ARGON2ID`` and ``SCRYPT`` are supported; ``ARGON2ID`` needs the
  ``argon2-cffi`` package, available through the ``argon2`` extra.

- Replay attack protection, enabled by default: a verified challenge is recorded
  in the Django cache by its signature and cannot be submitted twice.

- ``AltchaChallengeView``, for serving challenges from a URL rather than inlining
  them.

- Strict Content-Security-Policy support through ``ALTCHA_STRICT_CSP``. The
  widget then serves the modular ALTCHA build: the stylesheet is a separate file
  and the proof-of-work workers are loaded from the static files rather than from
  a ``blob:`` URL, so neither ``style-src 'unsafe-inline'`` nor
  ``worker-src blob:`` is needed.
  https://altcha.org/docs/v2/content-security-policy-csp/

- ``ALTCHA_INCLUDE_ASSETS``, for projects that load ALTCHA themselves — for
  instance by bundling the ``altcha`` npm package with webpack or Vite. The
  widget then emits no asset tags and its ``media`` is empty, while the
  ``<altcha-widget>`` element and its challenge are still rendered.

- Assets available either through the widget template or through Django's
  ``{{ form.media }}``.

- Every asset URL is configurable and resolved through ``STATIC_URL``, so hashed
  storages such as ``ManifestStaticFilesStorage`` and CDN hosting both work.

- Translations for 68 languages, either as a per-language file (1.4 KB gzipped)
  or as the combined bundle.

Maintenance
~~~~~~~~~~~

- The vendored ALTCHA version is pinned in ``package.json`` so that Dependabot
  and Renovate propose upgrades. ``just sync-altcha`` re-vendors the pinned
  version, verifying every file against the matching upstream git tag, and
  ``just check-altcha`` fails in CI when the vendored assets drift from the pin.
