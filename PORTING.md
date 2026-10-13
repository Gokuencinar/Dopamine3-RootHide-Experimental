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

## Local experimental progress (13 October 2026)

This branch now carries the RootHide 2 IPC client, process/blacklist/trust
sources, dyld loader hook candidates, package-manager hooks, and experimental
launchd integration alongside Dopamine 3's existing hookd/rootlesshooks.
It also includes the two RootHide bootstrap archives and the Sileo, Zebra,
and RootHide Manager packages. All five assets are SHA-256-pinned and attached
to the iOS application target. This is **not a compiled or working jailbreak**.

The RootHide IPC domain is isolated as ID `6`, and the XPC dispatcher now
rejects out-of-range domain and action indices. RootHide activation is tied
to a nonzero `jbrand` and a hidden `.jbroot-*` root path; that state is not
initialized by the stock Dopamine 3 bootstrap. Unresolved kernel offsets are
guarded where identified rather than used as kernel addresses.

The experimental RootHide bootstrap uses `.jbroot-<brand>` and a separate
AppGroup, rather than overwriting Dopamine's `/var/jb`; it rejects
unrecognized and incomplete installs, offers rollback, and installs RootHide
repositories and managers. It is **disabled by default** with
`ROOTHIDE3_BOOTSTRAP_READY=0`; stock Dopamine continues to use its original
Procursus path. The experimental path is deliberately limited to iOS 15/16;
iOS 17+ is rejected until separately ported.

**Remaining blockers:** The 3.x integration of RootHide 2 kernel/dyld
patches, code-signing/trust handling, bootstrap dependencies and jailbroken
runtime has not been compiled or tested. Some offsets required by the donor
are absent from Dopamine 3's kernel patchfinder and are guarded instead of
being used unchecked. RootHide's executable `bootstrapper` in the donor
was only a placeholder. The source audit reports 7 of 8 prerequisites;
the final activation check deliberately remains false. Enabling it based on
source presence alone would be unsafe. No RootHide IPA/TIPA has been built.

## Integration boundaries

1. **IPC and authorization.** Dopamine 3 reserves domain ID `5` for
   `JBS_DOMAIN_DOPAMINE`; RootHide 2 uses `5` for `JBS_DOMAIN_ROOTHIDE`.
	 RootHide uses domain ID `6` with a distinct server handler. Validate the
	 caller and operation permissions and test denial paths on hardware before
	 exposing privileged requests.
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

The first command prints source prerequisites; `--strict` exits nonzero
until the opt-in RootHide bootstrap has explicitly been enabled after device
validation. It deliberately blocks publication of an ordinary Dopamine IPA
as a RootHide release. Run `python3 -m unittest discover -s tools/tests` to
verify the IPC and source guard regressions. Neither check proves runtime
correctness or installation safety.

The next gates require a macOS build with Xcode, Theos, SDK, submodules and
RootHide-specific packages; inspection of the resulting `.tipa`, basebin
and entitlements; and device testing on supported arm64 and arm64e targets.
Start with iOS 15.x and iOS 16.x, then validate iOS 17+ separately.
For each target test bootstrap coexistence, first activation, reload,
respring, userspace reboot, disabled/enabled tweak injection, RootHide
blacklist, app and dylib trust, package installation, updates and uninstall.
Keep a recovery path and logs available before trying kernel changes.
