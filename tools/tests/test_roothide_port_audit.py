"""Regression checks for the critical Dopamine/RootHide IPC namespace clash."""

import unittest
from unittest.mock import patch

from tools import roothide_port_audit as audit


class IPCDomainTests(unittest.TestCase):
    def check_with_header(self, header: str) -> dict:
        with patch.object(audit, "read", return_value=header):
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


if __name__ == "__main__":
    unittest.main()
