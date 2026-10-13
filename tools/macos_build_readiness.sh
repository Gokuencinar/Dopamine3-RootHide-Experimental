#!/usr/bin/env bash
# Checks for compiling an experimental, *disabled* RootHide 3 port.
# Does not install anything, sign for a physical device or touch /var/jb.
set -euo pipefail

if [[ "$(uname -s)" != Darwin ]]; then
    echo "A macOS runner with Xcode is required; cannot build an iOS IPA here." >&2
    exit 3
fi

for tool in xcodebuild xcrun clang gmake ldid trustcache shasum; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Missing macOS build prerequisite: $tool" >&2
        exit 3
    fi
done

if [[ -z "${THEOS:-}" || ! -f "$THEOS/makefiles/common.mk" ]]; then
    echo "THEOS must point to the checked-out, pinned Theos tree" >&2
    exit 3
fi
expected_theos=304e0799973e8145f32e4ca2de6c747a84b758ce
if [[ "${GITHUB_REF_NAME:-}" == roothide-* || "${ROOTHIDE_EXPERIMENTAL_BUILD:-0}" == 1 ]]; then
    expected_theos=cfba89a53a05b4a1b822121158acc3669c20602f
fi
actual_theos="$(git -C "$THEOS" rev-parse HEAD)"
if [[ "$actual_theos" != "$expected_theos" ]]; then
    echo "Unexpected Theos revision: $actual_theos, expected $expected_theos" >&2
    exit 3
fi

if [[ -z "$(find "$THEOS/sdks" -type d -name '*.sdk' -print -quit)" ]]; then
    echo "Missing iPhoneOS SDK in THEOS/sdks" >&2
    exit 3
fi

python3 -m unittest discover -s tools/tests -p 'test_*.py'
python3 tools/roothide_port_audit.py
echo "Mac build environment and source checks passed; no device safety is implied."
