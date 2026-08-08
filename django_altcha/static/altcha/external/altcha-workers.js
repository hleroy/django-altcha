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
 * Worker URLs are resolved by django-altcha and passed in as a JSON mapping of
 * file name to URL, through the `data-altcha-workers` attribute. Resolving them
 * server-side keeps them correct under hashed staticfiles storages. When the
 * attribute is absent, the workers are looked up next to this module.
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

function getWorkerUrls() {
  const script = document.querySelector("script[data-altcha-workers]");
  if (script) {
    try {
      return JSON.parse(script.dataset.altchaWorkers);
    } catch {
      throw new Error("Unable to parse the data-altcha-workers mapping.");
    }
  }
  // No mapping provided: the workers sit next to this module, in ../workers/.
  const base = new URL("../workers/", import.meta.url).href;
  return Object.fromEntries(
    Object.values(ALGORITHMS).map((name) => [name, `${base}${name}`]),
  );
}

const workerUrls = getWorkerUrls();
const altcha = globalThis.$altcha;

if (!altcha || !altcha.algorithms) {
  throw new Error(
    "ALTCHA is not loaded. altcha-workers.js must be loaded after altcha.min.js.",
  );
}

for (const [algorithm, filename] of Object.entries(ALGORITHMS)) {
  const url = workerUrls[filename];
  if (url) {
    altcha.algorithms.set(algorithm, () => new Worker(url));
  }
}
