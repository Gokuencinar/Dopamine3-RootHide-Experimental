"""Keep iOS target framework links inside the iPhoneOS SDK, never the macOS SDK."""

from pathlib import Path
import re
import unittest


PROJECT = (Path(__file__).resolve().parents[2]
           / "Application/Dopamine.xcodeproj/project.pbxproj")

IOS_SDK = "System/Library/Frameworks/"

# Stable PBXFileReference IDs from the original Xcode project.
# IOKit, IOSurface and CoreML must resolve relative to the active iPhoneOS
# SDKROOT: BaseBin/dopamine also links -framework IOKit with -isysroot iphoneos.
REFERENCES = {
    "2F11A32A301C007500C1C9F0": ("IOKit", IOS_SDK, "SDKROOT"),
    "3165D0063020A584002737DA": ("IOKit", IOS_SDK, "SDKROOT"),
    "8C3B2E01301BC1B100C979A6": ("IOKit", IOS_SDK, "SDKROOT"),
    "8C5FA93F2BDD5039008C246F": ("IOKit", IOS_SDK, "SDKROOT"),
    "8C5FA9412BDD503D008C246F": ("IOSurface", IOS_SDK, "SDKROOT"),
    "8C5FA9432BDD5062008C246F": ("CoreML", IOS_SDK, "SDKROOT"),
    "8CDD08352B4F682000A32B61": ("IOSurface", IOS_SDK, "SDKROOT"),
    "8CDD08372B4F682500A32B61": ("IOKit", IOS_SDK, "SDKROOT"),
}

# The ClearSword reference is group-only; other frameworks have existing PBXBuildFiles
# shared across targets. Changing any fileRef or BuildFile ID breaks that linkage.
BUILD_FILES = {
    "2F11A32A301C007500C1C9F0": ("2F11A32B301C007500C1C9F0",),
    "3165D0063020A584002737DA": ("3165D0073020A584002737DA",),
    "8C3B2E01301BC1B100C979A6": (),
    "8C5FA93F2BDD5039008C246F": (
        "8C5FA9402BDD5039008C246F", "8C5FA96E2BDD7898008C246F",
        "8CF3E8512F72D45800931CA8",
    ),
    "8C5FA9412BDD503D008C246F": (
        "8C5FA9422BDD503D008C246F", "8C5FA96F2BDD789C008C246F",
        "8CF3E8502F72D45800931CA8",
    ),
    "8C5FA9432BDD5062008C246F": ("8C5FA9442BDD5062008C246F",),
    "8CDD08352B4F682000A32B61": ("8CDD08362B4F682000A32B61",),
    "8CDD08372B4F682500A32B61": (
        "8CC139832B53E05300230143", "8CDD08382B4F682500A32B61",
    ),
}


class XcodeFrameworkReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = PROJECT.read_text(encoding="utf-8")

    def test_framework_references_resolve_against_iphoneos_sdkroot(self) -> None:
        for identifier, (framework, prefix, tree) in REFERENCES.items():
            with self.subTest(identifier=identifier, framework=framework):
                entries = re.findall(
                    rf"^\s*{identifier} /\* {framework}\.framework \*/ = "
                    rf"\{{isa = PBXFileReference; ([^}}]*)\}};",
                    self.project, flags=re.MULTILINE,
                )
                self.assertEqual(len(entries), 1, "Missing or duplicated file reference")
                self.assertIn("lastKnownFileType = wrapper.framework;", entries[0])
                self.assertIn(f"path = {prefix}{framework}.framework;", entries[0])
                self.assertIn(f"sourceTree = {tree};", entries[0])

    def test_build_file_ids_and_file_refs_are_preserved(self) -> None:
        links = re.findall(
            r"^\s*([A-F0-9]{24}) /\* [^\n]*? \*/ = "
            r"\{isa = PBXBuildFile; fileRef = ([A-F0-9]{24}) /\*",
            self.project, flags=re.MULTILINE,
        )
        for reference_id, expected_ids in BUILD_FILES.items():
            with self.subTest(reference_id=reference_id):
                actual_ids = {build_id for build_id, file_ref in links
                              if file_ref == reference_id}
                self.assertEqual(actual_ids, set(expected_ids))
                for build_id in expected_ids:
                    self.assertGreaterEqual(self.project.count(build_id), 2,
                                            "BuildFile must remain in a build phase")
        # Keep the unlinked ClearSword IOKit reference in its PBXGroup too.
        self.assertIn("8C3B2E01301BC1B100C979A6 /* IOKit.framework */,", self.project)

    def test_every_iokit_reference_uses_iphoneos_sdkroot(self) -> None:
        actual = set(re.findall(
            r"^\s*([A-F0-9]{24}) /\* IOKit\.framework \*/ = "
            r"\{isa = PBXFileReference;",
            self.project, flags=re.MULTILINE,
        ))
        expected = {identifier for identifier, (name, _, _) in REFERENCES.items()
                    if name == "IOKit"}
        self.assertEqual(actual, expected,
                         "Unexpected IOKit reference could still link a macOS-only SDK")

    def test_no_host_macos_sdk_framework_references_remain(self) -> None:
        self.assertNotRegex(
            self.project,
            r"isa = PBXFileReference;[^\n]*path = [^;]*(?:MacOSX\.platform|"
            r"MacOSX(?:[0-9]+(?:\.[0-9]+)*)?\.sdk)[^;]*\.framework;",
        )


if __name__ == "__main__":
    unittest.main()
