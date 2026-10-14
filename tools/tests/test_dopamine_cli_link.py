"""Guard RootHide symbols required when linking the BaseBin dopamine CLI."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class DopamineCliLinkTests(unittest.TestCase):
    def test_cli_links_root_hide_functions_from_sibling_libjailbreak(self):
        cli = (ROOT / "BaseBin/dopamine/Makefile").read_text(encoding="utf-8")
        lib = (ROOT / "BaseBin/libjailbreak/Makefile").read_text(encoding="utf-8")
        code = (ROOT / "Application/Dopamine/Jailbreak/DOJailbreaker.m").read_text(encoding="utf-8")
        root = (ROOT / "BaseBin/libjailbreak/src/roothider/common.m").read_text(encoding="utf-8")
        self.assertRegex(cli, r"(?m)^LDFLAGS\s*=.*-L\.\./\.build\s+-ljailbreak\b")
        self.assertIn("src/roothider/*.m", lib)
        for name in ("ensure_dyld_trustcache", "exec_set_patch"):
            with self.subTest(symbol=name):
                self.assertIn(name + "(", code)
                self.assertIn(name + "(", root)

    def test_libjailbreak_install_name_resolves_next_to_cli(self):
        lib = (ROOT / "BaseBin/libjailbreak/Makefile").read_text(encoding="utf-8")
        packaging = (ROOT / "BaseBin/Makefile").read_text(encoding="utf-8")
        self.assertIn("-install_name @loader_path/$(TARGET)", lib)
        self.assertRegex(packaging, r"(?m)^dopamine:.*libjailbreak")
        self.assertIn("@cp dopamine/dopamine .build", packaging)
        self.assertIn("@cp libjailbreak/libjailbreak.dylib .build", packaging)


if __name__ == "__main__":
    unittest.main()
