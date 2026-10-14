#!/usr/bin/env python3
"""Inspect a compiled RootHide/Dopamine 3 IPA, not certify device functionality.

This check deliberately accepts a build with the RootHide enable flag *off*:
the result is a quarantined compilation artifact, never an install-ready
RootHide release. Runtime behavior needs physical-device validation.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import plistlib
import sys
import tarfile
import zipfile

try:
    from .roothide_port_audit import ROOT
except ImportError:
    from roothide_port_audit import ROOT  # direct command-line invocation


PINNED_RESOURCES = {
    "roothide_bootstrap_1800.tar.zst": "3350ed91d77163e0cd73f0f90185b5c9b87d9d294133e25ced3a29329e90370e",
    "roothide_bootstrap_1900.tar.zst": "420f72d1a62c9f884733cdefc596728469482a48858ec7ceca4d3ab2d3cba56c",
    "roothideapp.deb": "b8f075e1844709845962900b22fe71136a66369a2c35bb1201087f2fd9476b7d",
    "roothide_sileo.deb": "e85ab12f8d98da9a5350293647266b898282b0d766df2397526ab253d84eede3",
    "roothide_zebra.deb": "ca82c18256e19ff78af3e53308d53f047a2d429cb7e025c892377abe4d2e7825",
}

# BaseBin/dyldhook/Makefile builds all six variants and BaseBin/Makefile
# copies dyldhook/*.dylib into .build before creating basebin.tar. There is
# no single "dyldhook.dylib" in the archive.
REQUIRED_DYLDHOOK = (
    "dyldhook_merge.arm64e.iOS15.dylib",
    "dyldhook_merge.arm64.iOS15.dylib",
    "dyldhook_merge.arm64e.iOS16-17.dylib",
    "dyldhook_merge.arm64.iOS16-17.dylib",
    "dyldhook_merge.arm64e.iOS18+.dylib",
    "dyldhook_merge.arm64.iOS18+.dylib",
)

REQUIRED_BASEBIN = (
    "libjailbreak.dylib",
    "launchdhook.dylib",
    "systemhook.dylib",
    "roothidehooks.dylib",
    "rootlesshooks.dylib",
    "hookd",
    "jbctl",
    "bootstrapper",
    "dopamine",
    "jailbreakd",
    *REQUIRED_DYLDHOOK,
    "basebin.tc",
)

MACHO_MAGICS = (
    bytes.fromhex("cffaedfe"),  # little-endian Mach-O 64
    bytes.fromhex("feedfacf"),  # big-endian Mach-O 64
    bytes.fromhex("cafebabe"),  # fat header (including arm64/arm64e)
    bytes.fromhex("bebafeca"),
    bytes.fromhex("cafebabf"),  # fat64
    bytes.fromhex("bfbafeca"),
)


def is_macho(content: bytes) -> bool:
    return len(content) >= 32 and content[:4] in MACHO_MAGICS


def check_ipa(path: Path) -> tuple[list[str], dict]:
    errors: list[str] = []
    details: dict = {"ipa": str(path), "bytes": path.stat().st_size if path.exists() else 0}
    if not path.is_file():
        return ["IPA file does not exist"], details
    try:
        with zipfile.ZipFile(path) as ipa:
            bad = ipa.testzip()
            if bad:
                errors.append(f"IPA ZIP checksum failure: {bad}")
            names = set(ipa.namelist())
            prefix = "Payload/Dopamine.app/"
            info_path = prefix + "Info.plist"
            if info_path not in names:
                errors.append("IPA is missing the application Info.plist")
            else:
                info = plistlib.loads(ipa.read(info_path))
                executable = info.get("CFBundleExecutable")
                identifier = info.get("CFBundleIdentifier")
                details["bundle_id"] = identifier
                details["executable"] = executable
                if not isinstance(executable, str) or prefix + executable not in names:
                    errors.append("The declared app executable is absent")
                elif not is_macho(ipa.read(prefix + executable)):
                    errors.append("The app executable is not a valid Mach-O image")
            for filename, expected in PINNED_RESOURCES.items():
                resource = prefix + filename
                if resource not in names:
                    errors.append(f"Missing packaged RootHide resource: {filename}")
                elif hashlib.sha256(ipa.read(resource)).hexdigest() != expected:
                    errors.append(f"Resource hash mismatch: {filename}")
            basebin_resource = prefix + "basebin.tar"
            if basebin_resource not in names:
                errors.append("The app does not bundle basebin.tar")
            else:
                errors.extend(check_basebin_bytes(ipa.read(basebin_resource)))
            if prefix + "basebin.tc" not in names:
                errors.append("The app does not bundle basebin.tc")
    except (OSError, zipfile.BadZipFile, plistlib.InvalidFileException, ValueError) as exc:
        errors.append(f"Unable to inspect IPA: {exc}")
    return errors, details


def check_basebin_bytes(content: bytes) -> list[str]:
    try:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:*") as archive:
            files = {member.name.lstrip("./"): member for member in archive.getmembers() if member.isfile()}
            errors = []
            for name in REQUIRED_BASEBIN:
                key = f"basebin/{name}"
                member = files.get(key)
                if member is None:
                    errors.append(f"basebin.tar missing {name}")
                elif name != "basebin.tc":
                    extracted = archive.extractfile(member)
                    if not extracted or not is_macho(extracted.read(32)):
                        errors.append(f"basebin.tar contains invalid Mach-O: {name}")
            return errors
    except (tarfile.TarError, OSError) as exc:
        return [f"Invalid basebin.tar: {exc}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ipa", type=Path, default=ROOT / "Application/Dopamine.ipa")
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args()
    errors, details = check_ipa(options.ipa)
    source = (ROOT / "Application/Dopamine/Jailbreak/DOBootstrapper.m").read_text(encoding="utf-8")
    gate_disabled = "#define ROOTHIDE3_BOOTSTRAP_READY 0" in source
    if not gate_disabled:
        errors.append("The safety gate was changed; manual review is required")
    result = {
        "status": "PASS" if not errors else "FAIL",
        "classification": "COMPILE-ONLY / NOT INSTALLABLE AS ROOTHIDE",
        "roothide_activation_disabled": gate_disabled,
        "details": details,
        "errors": errors,
    }
    if options.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['status']}: {result['classification']}")
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
