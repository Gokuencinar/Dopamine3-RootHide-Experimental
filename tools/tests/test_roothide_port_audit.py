"""Regression checks for the critical Dopamine/RootHide IPC namespace clash."""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools import roothide_port_audit as audit


class IPCDomainTests(unittest.TestCase):
    def check_with_header(self, header: str, dispatcher: str = "gRootHideDomain") -> dict:
        def source(relative: str) -> str:
            return header if relative.endswith("jbserver_domains.h") else dispatcher

        with patch.object(audit, "read", side_effect=source):
            return audit.ipc_domain_check()

    def test_rejects_duplicate_dopamine_roothide_domain(self) -> None:
        result = self.check_with_header(
            "#define JBS_DOMAIN_DOPAMINE 5\n"
            "#define JBS_DOMAIN_ROOTHIDE 5\n"
        )
        self.assertFalse(result["ready"])
        self.assertTrue(any("shared" in item for item in result["missing"]))

    def test_accepts_distinct_namespace(self) -> None:
        result = self.check_with_header(
            "#define JBS_DOMAIN_PLATFORM 2\n"
            "#define JBS_DOMAIN_DOPAMINE 5\n"
            "#define JBS_DOMAIN_ROOTHIDE 6\n"
        )
        self.assertTrue(result["ready"])

    def test_rejects_missing_roothide_domain(self) -> None:
        result = self.check_with_header("#define JBS_DOMAIN_DOPAMINE 5\n")
        self.assertFalse(result["ready"])
        self.assertTrue(any("Add a RootHide" in item for item in result["missing"]))

    def test_rejects_unwired_domain_even_with_distinct_id(self) -> None:
        result = self.check_with_header(
            "#define JBS_DOMAIN_DOPAMINE 5\n#define JBS_DOMAIN_ROOTHIDE 6\n",
            dispatcher="",
        )
        self.assertFalse(result["ready"])
        self.assertTrue(any("Wire an authorized" in item for item in result["missing"]))

    def test_rejects_missing_device_logs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(audit, "ROOT", Path(directory)):
                result = audit.hardware_evidence_check()
        self.assertFalse(result["ready"])
        self.assertTrue(any("not supplied" in text for text in result["missing"]))

    def test_rejects_fake_device_pass_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "validation").mkdir()
            (root / "validation" / "device-tests.json").write_text(
                json.dumps({"tested_commit": "not-a-git-sha", "device_model": "test",
                            "ios_version": "16.0", "scenarios": {
                                "initial_boot": {"result": "pass", "log": "validation/logs/missing.txt",
                                                 "sha256": "00"}}}),
                encoding="utf-8",
            )
            with patch.object(audit, "ROOT", root):
                result = audit.hardware_evidence_check()
        self.assertFalse(result["ready"])
        self.assertTrue(any("hash" in problem or "Git" in problem
                            for problem in result["missing"]))


if __name__ == "__main__":
    unittest.main()
