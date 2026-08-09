#!/usr/bin/env python
"""
Vendor the ALTCHA front-end assets pinned in package.json.

The ALTCHA widget is vendored into ``django_altcha_widget/static/altcha/`` so that
``pip install django-altcha-widget`` works without a JavaScript toolchain. package.json
pins the version so that Dependabot can propose upgrades; this script turns such
a proposal into the matching asset update.

    python scripts/sync_altcha.py            # vendor the pinned version
    python scripts/sync_altcha.py --check    # verify the tree, offline

Assets are downloaded from the npm registry and each one is verified, byte for
byte, against the matching git tag served by jsDelivr. Publishing to npm and
tagging on GitHub are separate actions by the upstream maintainer, so agreement
between the two is a meaningful check that neither has been tampered with.
"""

import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = REPO_ROOT / "django_altcha_widget" / "static" / "altcha"
PACKAGE_JSON = REPO_ROOT / "package.json"
CHECKSUMS = STATIC_ROOT / "CHECKSUMS"
VENDOR_JSON = STATIC_ROOT / "VENDOR.json"

NPM_TARBALL_URL = "https://registry.npmjs.org/altcha/-/altcha-{version}.tgz"
JSDELIVR_URL = "https://cdn.jsdelivr.net/gh/altcha-org/altcha@v{version}/dist/{path}"
TAG_ARCHIVE_URL = (
    "https://github.com/altcha-org/altcha/archive/refs/tags/v{version}.tar.gz"
)

# Upstream dist path -> path under STATIC_ROOT.
ASSETS = {
    "main/altcha.min.js": "altcha.min.js",
    "external/altcha.min.js": "external/altcha.min.js",
    "external/altcha.css": "external/altcha.css",
    "workers/pbkdf2.js": "workers/pbkdf2.js",
    "workers/sha.js": "workers/sha.js",
    "workers/argon2id.js": "workers/argon2id.js",
    "workers/scrypt.js": "workers/scrypt.js",
}

# Every i18n file is vendored except the regional bundles, which sit between the
# per-language files and the combined all.js without being much use.
I18N_EXCLUDED = {"africa.js", "americas.js", "asia.js", "europe.js"}

# Assets provided by django-altcha-widget itself, never touched by a sync.
LOCAL_ASSETS = {"external/altcha-workers.js"}


def fail(message):
    sys.exit(f"error: {message}")


def get_pinned_version():
    """Return the exact altcha version pinned in package.json."""
    data = json.loads(PACKAGE_JSON.read_text())
    version = data.get("dependencies", {}).get("altcha")
    if not version:
        fail(f"no altcha dependency found in {PACKAGE_JSON}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        fail(
            f"altcha must be pinned to an exact version in {PACKAGE_JSON}, "
            f"got {version!r}"
        )
    return version


def download(url):
    with urllib.request.urlopen(url) as response:  # noqa: S310
        return response.read()


def get_npm_assets(version):
    """Return a mapping of upstream dist path to file content."""
    print(f"-> Downloading altcha {version} from the npm registry")
    tarball = download(NPM_TARBALL_URL.format(version=version))

    assets = {}
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            # Members are prefixed with "package/dist/".
            prefix = "package/dist/"
            if not member.name.startswith(prefix):
                continue
            path = member.name[len(prefix) :]
            if path in ASSETS or (
                path.startswith("i18n/")
                and path.endswith(".js")
                and Path(path).name not in I18N_EXCLUDED
            ):
                assets[path] = tar.extractfile(member).read()

    missing = set(ASSETS).difference(assets)
    if missing:
        fail(f"missing from the npm package: {', '.join(sorted(missing))}")
    return assets


def verify_against_tag(version, assets):
    """Check each asset against the upstream git tag, as served by jsDelivr."""
    print(f"-> Verifying {len(assets)} files against the v{version} tag")
    for path, content in sorted(assets.items()):
        url = JSDELIVR_URL.format(version=version, path=path)
        if hashlib.sha256(download(url)).digest() != hashlib.sha256(content).digest():
            fail(f"{path} differs between the npm package and the v{version} tag")


def write_assets(version, assets):
    """Write the assets into the static directory, replacing what is there."""
    targets = dict(ASSETS)
    for path in assets:
        if path.startswith("i18n/"):
            targets[path] = path

    # Drop translations that upstream no longer ships.
    for existing in (STATIC_ROOT / "i18n").glob("*.js"):
        if f"i18n/{existing.name}" not in targets:
            print(f"   removing {existing.relative_to(STATIC_ROOT)}")
            existing.unlink()

    for path, target in sorted(targets.items()):
        destination = STATIC_ROOT / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(assets[path])
    print(f"-> Wrote {len(targets)} files to {STATIC_ROOT.relative_to(REPO_ROOT)}")


def update_vendor_metadata(version):
    """Point VENDOR.json at the newly vendored version."""
    metadata = json.loads(VENDOR_JSON.read_text())
    metadata["version"] = version
    metadata["source"] = TAG_ARCHIVE_URL.format(version=version)
    metadata["purl"] = f"pkg:npm/altcha@{version}"
    VENDOR_JSON.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"-> Updated {VENDOR_JSON.relative_to(REPO_ROOT)}")


def iter_vendored_files():
    """Yield every vendored asset, excluding the ones django-altcha-widget provides."""
    for path in sorted(STATIC_ROOT.rglob("*")):
        if not path.is_file() or path in (CHECKSUMS, VENDOR_JSON):
            continue
        relative = path.relative_to(STATIC_ROOT).as_posix()
        if relative not in LOCAL_ASSETS:
            yield relative, path


def write_checksums(version):
    lines = [f"# altcha {version} - generated by scripts/sync_altcha.py\n"]
    for relative, path in iter_vendored_files():
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n")
    CHECKSUMS.write_text("".join(lines))
    print(f"-> Wrote {CHECKSUMS.relative_to(REPO_ROOT)}")


def check():
    """Verify the vendored tree matches package.json, without network access."""
    version = get_pinned_version()
    errors = []

    declared = json.loads(VENDOR_JSON.read_text())["version"]
    if declared != version:
        errors.append(
            f"{VENDOR_JSON.relative_to(REPO_ROOT)} declares version {declared}, "
            f"package.json pins {version}"
        )

    if not CHECKSUMS.exists():
        errors.append(f"{CHECKSUMS.relative_to(REPO_ROOT)} is missing")
    else:
        recorded = {}
        for line in CHECKSUMS.read_text().splitlines():
            if line and not line.startswith("#"):
                digest, _, relative = line.partition("  ")
                recorded[relative] = digest

        actual = {
            relative: hashlib.sha256(path.read_bytes()).hexdigest()
            for relative, path in iter_vendored_files()
        }
        for relative in sorted(set(recorded) | set(actual)):
            if relative not in actual:
                errors.append(f"{relative} is recorded but missing from static/")
            elif relative not in recorded:
                errors.append(f"{relative} is not recorded in CHECKSUMS")
            elif recorded[relative] != actual[relative]:
                errors.append(f"{relative} does not match its recorded checksum")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        sys.exit(
            f"\nThe vendored assets are out of sync with package.json (altcha "
            f"{version}).\nRun: python scripts/sync_altcha.py"
        )

    print(f"OK: vendored assets match altcha {version}")


def sync():
    version = get_pinned_version()
    if not shutil.which("npm"):
        print("note: npm is not required, assets come from the registry directly")
    assets = get_npm_assets(version)
    verify_against_tag(version, assets)
    write_assets(version, assets)
    update_vendor_metadata(version)
    write_checksums(version)
    print(f"\nDone. Review `git diff` and commit the altcha {version} assets.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the vendored assets match package.json, without downloading",
    )
    if parser.parse_args().check:
        check()
    else:
        sync()


if __name__ == "__main__":
    main()
