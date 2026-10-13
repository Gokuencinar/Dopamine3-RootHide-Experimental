#!/usr/bin/env python3
"""Static prerequisites for the RootHide 2 -> Dopamine 3 port.

An all-green report means only that the listed components are connected in
source. It does not establish that a jailbreak is safe or works on a device.
"""

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOMAIN_RE = re.compile(r"^\s*#define\s+(JBS_DOMAIN_\w+)\s+(\d+)\b", re.M)


def read(relative: str) -> str:
    path = ROOT / relative
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def require(label: str, files: tuple[str, ...], text_checks: tuple[tuple[str, str], ...] = ()) -> dict:
    absent = [path for path in files if not (ROOT / path).is_file()]
    absent += [f"{path} (missing {token!r})" for path, token in text_checks if token not in read(path)]
    return {"component": label, "ready": not absent, "missing": absent}


def ipc_domain_check() -> dict:
    path = "BaseBin/libjailbreak/src/jbserver_domains.h"
    domains = {name: int(value) for name, value in DOMAIN_RE.findall(read(path))}
    problems = []
    if "JBS_DOMAIN_DOPAMINE" not in domains:
        problems.append("Preserve the Dopamine app IPC domain")
    if "JBS_DOMAIN_ROOTHIDE" not in domains:
        problems.append("Add a RootHide IPC domain and its explicit authorization policy")
    by_id: dict[int, list[str]] = {}
    for name, value in domains.items():
        by_id.setdefault(value, []).append(name)
    for number, names in by_id.items():
        if len(names) > 1:
            problems.append(f"IPC domain number {number} is shared: {', '.join(names)}")
    if "gRootHideDomain" not in read("BaseBin/launchdhook/src/jbserver/jbserver_global.c"):
        problems.append("Wire an authorized RootHide server domain before enabling the client")
    return {"component": "XPC domain separation", "ready": not problems, "missing": problems}


def inspect() -> list[dict]:
    return [
        ipc_domain_check(),
        require(
            "RootHide state and trust client",
            (
                "BaseBin/libjailbreak/src/jbclient_roothide.c",
                "BaseBin/libjailbreak/src/roothider/common.h",
                "BaseBin/libjailbreak/src/roothider/exec_patch.m",
            ),
            (("BaseBin/libjailbreak/Makefile", "src/roothider/"),),
        ),
        require(
            "Hidden bootstrap and randomized root",
            ("Application/Dopamine/Jailbreak/DOBootstrapper.m",),
            (
                ("Application/Dopamine/Jailbreak/DOBootstrapper.m", ".jbroot-"),
                ("Application/Dopamine/Jailbreak/DOBootstrapper.m", "RH3NewBrand"),
                ("Application/Dopamine/Jailbreak/DOEnvironmentManager.m", "rootHideBrandForPath"),
            ),
        ),
        require(
            "Dopamine 3-compatible RootHide process and dyld integration",
            (
                "BaseBin/systemhook/src/roothider_port.c",
                "BaseBin/dyldhook/src/roothider.c",
                "BaseBin/dyldhook/src/roothider.S",
            ),
            (
                ("BaseBin/systemhook/src/main.c", "roothide_prepare_process"),
                ("BaseBin/dyldhook/src/main.c", "dyldhook_init_roothide"),
            ),
        ),
        require(
            "RootHide launchd and IPC integration",
            (
                "BaseBin/launchdhook/src/jbserver/jbdomain_roothide.c",
                "BaseBin/jailbreakd/src/server.m",
            ),
            (
                ("BaseBin/launchdhook/src/main.m", "initJailbreakd(firstLoad)"),
                ("BaseBin/launchdhook/src/spawn_hook.c", "commitBlacklistProcessId"),
                ("BaseBin/libjailbreak/src/roothider/common.m", "roothide_is_active"),
            ),
        ),
        require(
            "Filesystem and package-manager hooks",
            (
                "BaseBin/roothidehooks/Makefile",
                "BaseBin/roothidehooks/pathhook.x",
                "BaseBin/roothidehooks/installd.x",
                "BaseBin/roothidehooks/lsd.x",
                "BaseBin/roothidehooks/cfprefsd.x",
            ),
            (("BaseBin/Makefile", "roothidehooks"),),
        ),
        require(
            "RootHide-specific bootstrap packages and manager",
            ("Application/Dopamine/Resources/roothideapp.deb",),
            (
                ("Application/Dopamine/Jailbreak/DOBootstrapper.m", "roothideapp.deb"),
                ("Application/Dopamine/Jailbreak/DOBootstrapper.m", "roothide.github.io"),
            ),
        ),
        require(
            "Explicit RootHide activation gate",
            ("Application/Dopamine/Jailbreak/DOBootstrapper.m",),
            (
                ("Application/Dopamine/Jailbreak/DOBootstrapper.m", "#define ROOTHIDE3_BOOTSTRAP_READY 1"),
            ),
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Fail if any port prerequisite is missing")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report")
    args = parser.parse_args()

    checks = inspect()
    complete = sum(check["ready"] for check in checks)
    if args.json:
        print(json.dumps({"static_prerequisites": f"{complete}/{len(checks)}", "checks": checks}, indent=2))
    else:
        print(f"RootHide/Dopamine 3 static prerequisites: {complete}/{len(checks)}")
        for check in checks:
            print(f"  {'PASS' if check['ready'] else 'MISSING'}  {check['component']}")
            for detail in check["missing"]:
                print(f"           {detail}")
        print("Static checks do not prove build, installation, kernel stability, or hiding effectiveness.")
    return 2 if args.strict and complete != len(checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
