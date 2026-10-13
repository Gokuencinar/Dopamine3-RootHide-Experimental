"""Regression checks for the critical Dopamine/RootHide IPC namespace clash."""

import unittest
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


if __name__ == "__main__":
    unittest.main()
