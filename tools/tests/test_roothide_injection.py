"""Regression guards for the RootHide/stock systemhook injection boundary.

The shared C hook runs in launchd as well as systemhook, so the path decision
must not depend on asking launchd's XPC server to identify itself. These tests
check the integration contract; an actual iOS build/device test is separate.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


def source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class RootHideInjectionTests(unittest.TestCase):
    def test_shared_path_selector_preserves_stock_and_private_roothide(self) -> None:
        header = source("BaseBin/systemhook/src/common/common.h")
        common = source("BaseBin/systemhook/src/common/common.c")

        self.assertIn('#define STOCK_HOOK_DYLIB_PATH "/usr/lib/systemhook.dylib"', header)
        self.assertIn("#define HOOK_DYLIB_PATH systemhook_dylib_path()", header)
        self.assertIn("const char *systemhook_dylib_path(void)", common)
        self.assertIn("is_roothide_root_path(get_jbroot())", common)
        self.assertIn('JBROOT_PATH("/basebin/systemhook.dylib")', common)
        self.assertIn("return STOCK_HOOK_DYLIB_PATH;", common)
        self.assertIn("_Thread_local char resolvedPath[PATH_MAX]", common)

        # Both canonical and /private-prefixed container paths are accepted,
        # but arbitrary paths and substrings do not trigger RootHide injection.
        self.assertIn('"/var/containers/Bundle/Application/.jbroot-"', common)
        self.assertIn('"/private/var/containers/Bundle/Application/.jbroot-"', common)
        self.assertIn("strlen(brand) != 16", common)
        self.assertIn("brand[i] >= 'A' && brand[i] <= 'F'", common)

    def test_spawn_and_exec_use_the_selected_path_consistently(self) -> None:
        common = source("BaseBin/systemhook/src/common/common.c")
        hook = common.split("static int spawn_exec_hook_common(", 1)[1].split(
            "int posix_spawn_hook_shared(", 1
        )[0]
        self.assertIn("const char *hookDylibPath = HOOK_DYLIB_PATH;", hook)
        self.assertIn("access(hookDylibPath, F_OK)", hook)
        self.assertIn("strcmp(existingLibraryInsert, hookDylibPath)", hook)
        self.assertIn("strcpy(newLibraryInsert, hookDylibPath)", hook)
        self.assertIn("strcmp(existingLibraryInserts, hookDylibPath)", hook)
        self.assertNotIn("access(HOOK_DYLIB_PATH", hook)
        self.assertNotIn('"/usr/lib/systemhook.dylib"', hook)

        # Both launchd and already-injected processes call the same helper.
        self.assertIn("spawn_exec_hook_common(false,", common)
        self.assertIn("spawn_exec_hook_common(true,", common)

    def test_reboot_does_not_mount_fakelib_in_roothide(self) -> None:
        launchd = source("BaseBin/launchdhook/src/spawn_hook.c")
        mounting = launchd.split("void ensure_fakelib_mounted(void)", 1)[1].split(
            "int __posix_spawn_orig_wrapper(", 1
        )[0]
        self.assertRegex(
            mounting,
            re.compile(r"if\s*\(roothide_is_active\(\)\)\s*return\s*;"),
        )
        self.assertLess(mounting.index("roothide_is_active()"), mounting.index('statfs("/usr/lib"'))
        self.assertIn('"fakelib", "mount"', mounting)
        self.assertIn("ensure_fakelib_mounted();", launchd)

    def test_existing_blacklist_and_gate_remain_intact(self) -> None:
        launchd = source("BaseBin/launchdhook/src/spawn_hook.c")
        self.assertIn("roothide_is_active() && isBlacklistedPath(path)", launchd)
        self.assertIn('strncmp(envp[i], "DYLD_INSERT_LIBRARIES=", 22)', launchd)
        self.assertIn("roothide_spawn_uninjected(trackedPid, path, desc, argv, envp)", launchd)
        self.assertIn("posix_spawn_hook_shared(pid, path, desc, argv, envp", launchd)
        bootstrap = source("Application/Dopamine/Jailbreak/DOBootstrapper.m")
        self.assertIn("#define ROOTHIDE3_BOOTSTRAP_READY 0", bootstrap)


if __name__ == "__main__":
    unittest.main()
