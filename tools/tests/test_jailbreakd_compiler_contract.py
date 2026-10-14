"""Guard the jailbreakd Objective-C ARC and reporter build contracts.

These assertions supplement, but cannot replace, a macOS/iOS compiler run.
"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class JailbreakdCompilerContractTests(unittest.TestCase):
    def source(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_donor_crash_reporter_does_not_leak_into_dopamine3_binary(self):
        main = self.source("BaseBin/jailbreakd/src/main.m")
        makefile = self.source("BaseBin/libjailbreak/Makefile")
        self.assertNotIn("crashreporter_start();", main)
        self.assertIn("$(filter-out src/roothider/crashreporter.m,", makefile)

    def test_arc_managed_xpc_messages_do_not_use_manual_retain_release(self):
        server = self.source("BaseBin/jailbreakd/src/server.m")
        makefile = self.source("BaseBin/jailbreakd/Makefile")
        self.assertIn("-fobjc-arc", makefile)
        self.assertNotIn("xpc_retain(", server)
        self.assertNotIn("xpc_release(", server)
        self.assertIn("xpc_object_t asyncMessage = message;", server)
        self.assertIn("xpc_object_t asyncReply = reply;", server)
        self.assertIn("dispatch_async(", server)
        self.assertIn("jailbreakd_reply_message(msgId, asyncReply)", server)


if __name__ == "__main__":
    unittest.main()
