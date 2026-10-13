# RootHide 3 experimental hardware gate

There are **no successful device tests** recorded for this port. Do not create
or commit fictitious pass results to make the CI gate green. The static
`--strict` gate requires both code activation review and real logs tied to
the exact tested commit.

After a compiled and independently inspected IPA is available, authorized
testers should validate on disposable/recoverable arm64e iOS 15/16 devices
with a full backup and an explicit recovery plan. Test the initial boot, the
isolated hidden bootstrap, filesystem/process hiding, RootHide package
manager installation, tweak injection and blacklist, subsequent boot and
userspace reboot, uninstall/recovery, and the coexistence policy with
ordinary Dopamine.

Only when all checks truly pass, save a redacted log for each under
`validation/logs/`, calculate its SHA-256, and create
`validation/device-tests.json` with the schema:

```json
{
  "tested_commit": "40-character-Git-SHA",
  "device_model": "exact-iPhone-model",
  "ios_version": "exact-iOS-version",
  "scenarios": {
    "initial_boot": {
      "result": "pass",
      "log": "validation/logs/initial_boot.txt",
      "sha256": "64-character-sha256"
    }
  }
}
```

The eight scenario keys are defined in `tools/roothide_port_audit.py`.
Each must have real matching evidence. Log hashing is an integrity check,
**not** a guarantee of correctness or cryptographic attestation of a device.
Never commit device identifiers, passwords, tokens or personal app data.

The `tested_commit` must be an ancestor of the current branch. Only commits
touching `validation/` may follow that tested source revision; any source
change invalidates the evidence, forcing a fresh device validation.
