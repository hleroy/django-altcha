/*
 * Copyright (c) nexB Inc. and others. All rights reserved.
 * SPDX-License-Identifier: MIT
 * See https://github.com/aboutcode-org/django-altcha for support or download.
 *
 * Registers the ALTCHA Proof-of-Work workers for the modular "external" build.
 *
 * The default ALTCHA bundle inlines its workers and instantiates them from a
 * `blob:` URL, which requires `worker-src blob:` in the Content-Security-Policy.
 * The external build ships no workers at all and registers no algorithm, so the
 * integrator has to point `$altcha.algorithms` at plain worker scripts served
 * from the same origin.
 *
 * This module must be loaded *after* `external/altcha.min.js`, which creates the
 * `$altcha` global. Both are `type="module"` scripts without `async`, so the
 * browser evaluates them in document order.
 *
 * The worker directory is resolved, in order of precedence, from:
 *   1. the `data-altcha-workers-url` attribute of any script tag on the page,
 *   2. this module's own URL (`../workers/` next to `external/`).
 */
const ALGORITHMS = {
  "SHA-256": "sha.js",
  "SHA-384": "sha.js",
  "SHA-512": "sha.js",
  "PBKDF2/SHA-256": "pbkdf2.js",
  "PBKDF2/SHA-384": "pbkdf2.js",
  "PBKDF2/SHA-512": "pbkdf2.js",
  ARGON2ID: "argon2id.js",
  SCRYPT: "scrypt.js",
};

function getWorkersUrl() {
  const script = document.querySelector("script[data-altcha-workers-url]");
  const configured = script && script.dataset.altchaWorkersUrl;
  const base = configured || new URL("../workers/", import.meta.url).href;
  return base.endsWith("/") ? base : `${base}/`;
}

const workersUrl = getWorkersUrl();
const altcha = globalThis.$altcha;

if (!altcha || !altcha.algorithms) {
  throw new Error(
    "ALTCHA is not loaded. altcha-workers.js must be loaded after altcha.min.js.",
  );
}

for (const [algorithm, filename] of Object.entries(ALGORITHMS)) {
  altcha.algorithms.set(
    algorithm,
    () => new Worker(new URL(filename, workersUrl)),
  );
}
