"""Static regressions for the staged Dopamine 3 / RootHide integration.

These assertions verify source-level safety gates, not actual jailbreak
functionality. Device testing remains necessary before any release.
"""

import hashlib
import unittest

from tools import roothide_port_audit as audit


class RootHideGuardTests(unittest.TestCase):
    def source(self, name: str) -> str:
        content = audit.read(name)
        self.assertTrue(content, f"Missing source: {name}")
        return content

    def test_bootstrap_opt_in_defaults_off(self) -> None:
        bootstrap = self.source("Application/Dopamine/Jailbreak/DOBootstrapper.m")
        self.assertIn("#define ROOTHIDE3_BOOTSTRAP_READY 0", bootstrap)

    def test_hidden_root_requires_brand_and_exact_location(self) -> None:
        source = self.source("BaseBin/libjailbreak/src/roothider/common.m")
        self.assertIn("bool roothide_is_active(void)", source)
        self.assertIn("jbrand == 0", source)
        self.assertIn("/.jbroot-%016llX", source)
        self.assertIn("strcmp(rootPath, root)", source)

    def test_dispatcher_checks_domain_and_action_indices(self) -> None:
        source = self.source("BaseBin/libjailbreak/src/jbserver.c")
        self.assertIn("domainIdx > server->maxDomain", source)
        self.assertIn("actionIdx > jbserver_last_action_for_domain(domainIdx)", source)

    def test_roothide_ipc_rejects_invalid_client_inputs(self) -> None:
        source = self.source("BaseBin/launchdhook/src/jbserver/jbdomain_roothide.c")
        self.assertIn("if (!roothide_is_active()) return false", source)
        self.assertIn("preferredArchCount > 16", source)
        self.assertIn("xpc_get_type(checkvalue) != XPC_TYPE_UINT64", source)
        self.assertIn("proc_pidpath_audittoken(callerToken", source)

    def test_blacklisted_spawn_tracks_child_pid(self) -> None:
        source = self.source("BaseBin/launchdhook/src/spawn_hook.c")
        self.assertIn("roothide_is_active() && isBlacklistedPath(path)", source)
        self.assertIn("allocBlacklistProcessId()", source)
        self.assertIn("commitBlacklistProcessId(trackedPid)", source)

    def test_root_hide_never_exposes_var_jb_via_settings(self) -> None:
        manager = self.source("Application/Dopamine/Jailbreak/DOEnvironmentManager.m")
        settings = self.source("Application/Dopamine/UI/Settings/DOSettingsController.m")
        self.assertIn("if ([DOBootstrapper rootHidePortEnabled]) return YES;", manager)
        self.assertIn("if ([DOBootstrapper rootHidePortEnabled]) return;", manager)
        self.assertIn("![DOBootstrapper rootHidePortEnabled] &&", settings)

    def test_hidden_bootstrap_disables_stock_procursus_repositories(self) -> None:
        bootstrap = self.source("Application/Dopamine/Jailbreak/DOBootstrapper.m")
        self.assertIn('@"etc/apt/sources.list.d/procursus.sources"', bootstrap)
        self.assertIn('@"etc/apt/sources.list.d/procursus.list"', bootstrap)
        self.assertIn('@"etc/apt/sources.list"', bootstrap)
        self.assertIn("https://roothide.github.io/procursus", bootstrap)

    def test_root_hide_skips_stock_fakelib_and_protection(self) -> None:
        source = self.source("Application/Dopamine/Jailbreak/DOJailbreaker.m")
        self.assertIn("Initializing RootHide dyld support", source)
        self.assertIn("ensure_dyld_trustcache(", source)
        self.assertIn("exec_set_patch(true)", source)
        self.assertIn('setenv("DYLD_IN_CACHE", "0"', source)
        self.assertIn("Preserve Dopamine 3's conventional protection", source)

    def test_donor_bootstrap_self_deletion_does_not_block_install_marker(self) -> None:
        source = self.source("Application/Dopamine/Jailbreak/DOBootstrapper.m")
        self.assertIn("BOOL ranInitialSetup = NO", source)
        self.assertIn("ranInitialSetup = YES", source)
        self.assertIn("if (!ranInitialSetup && ![fm fileExistsAtPath:marker])", source)
        self.assertIn("if (ranInitialSetup) {", source)

    def test_macos_ci_unpacks_xz_sdk_with_correct_decoder(self) -> None:
        workflow = self.source(".github/workflows/main.yml")
        self.assertIn('tar -xJf "$THEOS/sdks/iPhoneOS16.5.sdk.tar.xz"', workflow)
        self.assertNotIn("gunzip $THEOS/sdks/iPhoneOS16.5.sdk.tar.xz", workflow)

    def test_roothide_assets_have_expected_hashes_and_are_in_app_target(self) -> None:
        hashes = {
            "roothide_bootstrap_1800.tar.zst": "3350ed91d77163e0cd73f0f90185b5c9b87d9d294133e25ced3a29329e90370e",
            "roothide_bootstrap_1900.tar.zst": "420f72d1a62c9f884733cdefc596728469482a48858ec7ceca4d3ab2d3cba56c",
            "roothideapp.deb": "b8f075e1844709845962900b22fe71136a66369a2c35bb1201087f2fd9476b7d",
            "roothide_sileo.deb": "e85ab12f8d98da9a5350293647266b898282b0d766df2397526ab253d84eede3",
            "roothide_zebra.deb": "ca82c18256e19ff78af3e53308d53f047a2d429cb7e025c892377abe4d2e7825",
        }
        project = self.source("Application/Dopamine.xcodeproj/project.pbxproj")
        for filename, expected_sha256 in hashes.items():
            with self.subTest(filename=filename):
                path = audit.ROOT / "Application/Dopamine/Resources" / filename
                self.assertTrue(path.is_file(), f"Missing bundled asset: {filename}")
                hasher = hashlib.sha256()
                with path.open("rb") as file:
                    for block in iter(lambda: file.read(1024 * 1024), b""):
                        hasher.update(block)
                self.assertEqual(hasher.hexdigest(), expected_sha256)
                self.assertIn(f"/* {filename} in Resources */", project)


if __name__ == "__main__":
    unittest.main()
