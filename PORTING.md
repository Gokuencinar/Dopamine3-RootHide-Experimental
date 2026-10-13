# RootHide for Dopamine 3: integration worktree

**Status: incomplete, not installable as RootHide.** This worktree is the
beginning of a port. Do not distribute its normal Dopamine IPA as a RootHide
release or run it as a RootHide updater.

## Source provenance

| Role | Repository / branch | Pinned source commit |
| --- | --- | --- |
| RootHide 3.x starting point | `roothide/Dopamine-roothide` `3.x` | `7e0a9243594b271b3db673bb5194b00be6096ab8` |
| Dopamine 3 base | `opa334/Dopamine` `3.x` | `448ff1a83d2bb807346f1f3d36332e4afbf9794a` (3.0.11) |
| Working RootHide donor | `roothide/Dopamine2-roothide` `v2.4.9.x` | `e8de6e5035fee52ca732536dbb3ca1734889d914` |

The public RootHide 3.x branch contains no RootHide implementation commits
relative to its Dopamine 3 ancestor; its only fork-specific commit empties
`README.md`. The RootHide 2.x implementation cannot be transplanted unchanged.

## Integration boundaries

1. **IPC and authorization.** Dopamine 3 reserves domain ID `5` for
   `JBS_DOMAIN_DOPAMINE`; RootHide 2 uses `5` for `JBS_DOMAIN_ROOTHIDE`.
   Preserve existing Dopamine requests, assign RootHide a unique domain,
   update all client/server dispatch and authorization checks, and test that
   unprivileged clients cannot invoke privileged actions.
2. **Shared jailbreak state.** Preserve Dopamine 3 `info.h` state, kernel
   offsets and SPTM/TXM code while integrating RootHide `jbrand`, trust,
   dyld-patching and blacklist state. Check serialization and rollback.
3. **Hidden bootstrap and filesystem.** Adapt RootHide's `.jbroot-...`
   installation, auxiliary container paths, package repositories and
   RootHide Manager. Cover fresh install, existing Dopamine bootstrap,
   switching after reboot, updates, and complete removal without deleting
   another environment.
4. **Runtime integration.** Port RootHide 2's `roothider/*`,
   `jbclient_roothide.c`, `roothidehooks`, `launchdhook` and `dyldhook`.
   Reconcile with Dopamine 3 `hookd`, `rootlesshooks`, `litehook` and dynamic
   trustcaches, including the newer iOS kernel/loader variations.
5. **Build and packaging.** Select matching RootHide Procursus,
   Theos package scheme, replacement manager, entitlements and
   arm64/arm64e binaries. Audit all resources and build artifacts.

## Verification gates

From this repository, run:

```
python3 tools/roothide_port_audit.py
python3 tools/roothide_port_audit.py --strict
```

The first command prints missing source prerequisites; `--strict` exits
with code `2` until the source integrations are present. It is deliberately
not a functionality test, and source completion is only the first gate.

The next gates require a macOS build with Xcode, Theos, SDK, submodules and
RootHide-specific packages; inspection of the resulting `.tipa`, basebin
and entitlements; and device testing on supported arm64 and arm64e targets.
Start with iOS 15.x and iOS 16.x, then validate iOS 17+ separately.
For each target test bootstrap coexistence, first activation, reload,
respring, userspace reboot, disabled/enabled tweak injection, RootHide
blacklist, app and dylib trust, package installation, updates and uninstall.
Keep a recovery path and logs available before trying kernel changes.
