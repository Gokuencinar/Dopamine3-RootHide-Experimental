"""Keep iOS framework links independent of versioned host macOS SDK paths."""

from pathlib import Path
import re
import unittest


PROJECT = (Path(__file__).resolve().parents[2]
           / "Application/Dopamine.xcodeproj/project.pbxproj")

IOS_SDK = "System/Library/Frameworks/"
MAC_SDK = "Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/System/Library/Frameworks/"

# Stable PBXFileReference IDs from the original Xcode project.
# IOKit is taken from the host Mac SDK, while IOSurface/CoreML use iPhoneOS SDKROOT.
REFERENCES = {
    "8C3B2E01301BC1B100C979A6": ("IOKit", MAC_SDK, "DEVELOPER_DIR"),
    "8C5FA93F2BDD5039008C246F": ("IOKit", MAC_SDK, "DEVELOPER_DIR"),
    "8C5FA9412BDD503D008C246F": ("IOSurface", IOS_SDK, "SDKROOT"),
    "8C5FA9432BDD5062008C246F": ("CoreML", IOS_SDK, "SDKROOT"),
    "8CDD08352B4F682000A32B61": ("IOSurface", IOS_SDK, "SDKROOT"),
    "8CDD08372B4F682500A32B61": ("IOKit", MAC_SDK, "DEVELOPER_DIR"),
}

# The first reference is group-only; other frameworks have existing PBXBuildFiles
# shared across targets. Changing any fileRef or BuildFile ID breaks that linkage.
BUILD_FILES = {
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

    def test_remaining_framework_references_use_stable_sdk_paths(self) -> None:
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

    def test_no_version_pinned_host_sdk_frameworks_remain(self) -> None:
        self.assertNotRegex(
            self.project,
            r"isa = PBXFileReference;[^\n]*path = Platforms/MacOSX\.platform/"
            r"Developer/SDKs/MacOSX[0-9]+(?:\.[0-9]+)*\.sdk/"
            r"System/Library/Frameworks/",
        )


if __name__ == "__main__":
    unittest.main()
