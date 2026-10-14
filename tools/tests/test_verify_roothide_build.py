"""Hermetic tests for the post-build IPA inspection (not device tests)."""

import hashlib
import io
import plistlib
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools import verify_roothide_build as verifier


# Explicit fixture contents, independent of the verifier's required-file list:
# a mistakenly removed validation entry must still fail the missing-file tests.
NEW_REQUIRED_BASEBIN_FILES = (
    "bootstrapper",
    "dopamine",
    "jailbreakd",
    "dyldhook_merge.arm64e.iOS15.dylib",
    "dyldhook_merge.arm64.iOS15.dylib",
    "dyldhook_merge.arm64e.iOS16-17.dylib",
    "dyldhook_merge.arm64.iOS16-17.dylib",
    "dyldhook_merge.arm64e.iOS18+.dylib",
    "dyldhook_merge.arm64.iOS18+.dylib",
)

BASEBIN_FIXTURE_FILES = (
    "libjailbreak.dylib",
    "launchdhook.dylib",
    "systemhook.dylib",
    "roothidehooks.dylib",
    "rootlesshooks.dylib",
    "hookd",
    "jbctl",
    *NEW_REQUIRED_BASEBIN_FILES,
    "basebin.tc",
)


def sample_basebin(missing=None, corrupt=None):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode="w") as archive:
        for name in BASEBIN_FIXTURE_FILES:
            if name == missing:
                continue
            if name == "basebin.tc":
                payload = b"trustcache-fixture"
            elif name == corrupt:
                payload = b"invalid-Mach-O" + b"x" * 64
            else:
                payload = bytes.fromhex("cffaedfe") + b"x" * 64
            header = tarfile.TarInfo("basebin/" + name)
            header.size = len(payload)
            archive.addfile(header, io.BytesIO(payload))
    return result.getvalue()


def sample_ipa(path: Path, *, missing=None, corrupt=None, missing_basebin=None, corrupt_basebin=None):
    payload = b"dummy-test-resource"
    expected = hashlib.sha256(payload).hexdigest()
    with patch.dict(verifier.PINNED_RESOURCES,
                    {name: expected for name in verifier.PINNED_RESOURCES}):
        with zipfile.ZipFile(path, "w") as archive:
            prefix = "Payload/Dopamine.app/"
            archive.writestr(prefix + "Info.plist", plistlib.dumps({
                "CFBundleExecutable": "Dopamine",
                "CFBundleIdentifier": "com.opa334.Dopamine",
            }))
            archive.writestr(prefix + "Dopamine", bytes.fromhex("cffaedfe") + b"x" * 64)
            archive.writestr(prefix + "basebin.tar", sample_basebin(missing_basebin, corrupt_basebin))
            archive.writestr(prefix + "basebin.tc", b"test-trustcache")
            for name in verifier.PINNED_RESOURCES:
                if name != missing:
                    archive.writestr(prefix + name,
                                     payload if name != corrupt else b"wrong")
        return verifier.check_ipa(path)[0]


class BuildArtifactVerificationTests(unittest.TestCase):
    def test_complete_quarantined_build_has_no_missing_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(sample_ipa(Path(directory) / "Dopamine.ipa"), [])

    def test_missing_roothide_manager_is_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = sample_ipa(Path(directory) / "Dopamine.ipa", missing="roothideapp.deb")
            self.assertTrue(any("roothideapp.deb" in message for message in errors))

    def test_resource_sha_mismatch_is_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = sample_ipa(Path(directory) / "Dopamine.ipa", corrupt="roothide_sileo.deb")
            self.assertTrue(any("hash mismatch" in message for message in errors))

    def test_missing_roothidehooks_dylib_is_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = sample_ipa(Path(directory) / "Dopamine.ipa", missing_basebin="roothidehooks.dylib")
            self.assertTrue(any("roothidehooks.dylib" in message for message in errors))

    def test_missing_bootstrapper_daemons_or_dyldhook_variants_are_blocking(self):
        for name in NEW_REQUIRED_BASEBIN_FILES:
            with self.subTest(missing=name), tempfile.TemporaryDirectory() as directory:
                errors = sample_ipa(Path(directory) / "Dopamine.ipa", missing_basebin=name)
                self.assertIn(f"basebin.tar missing {name}", errors)

    def test_invalid_macho_in_bootstrapper_daemons_or_dyldhook_is_blocking(self):
        for name in NEW_REQUIRED_BASEBIN_FILES:
            with self.subTest(corrupt=name), tempfile.TemporaryDirectory() as directory:
                errors = sample_ipa(Path(directory) / "Dopamine.ipa", corrupt_basebin=name)
                self.assertIn(f"basebin.tar contains invalid Mach-O: {name}", errors)

    def test_malformed_tar_is_blocking(self):
        self.assertTrue(any("Invalid basebin.tar" in message
                            for message in verifier.check_basebin_bytes(b"wrong")))

    def test_non_macho_image_is_rejected(self):
        self.assertFalse(verifier.is_macho(b"HELLO" + b"0" * 60))
        self.assertTrue(verifier.is_macho(bytes.fromhex("cafebabe") + b"0" * 64))


if __name__ == "__main__":
    unittest.main()
