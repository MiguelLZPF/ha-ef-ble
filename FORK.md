# Fork notes

## Table of Contents

- [Why this fork exists](#why-this-fork-exists)
- [Rebasing onto a new upstream tag](#rebasing-onto-a-new-upstream-tag)
- [What differs](#what-differs)

## Why this fork exists

This fork adds local (Bluetooth) support for the EcoFlow Smart Meter Dual CT (ES81),
taken from upstream PR #551 (author CFLLDS, commit 71a149a). Upstream does not accept new
devices, so the module lives here to stop an upstream update from deleting it.

## Rebasing onto a new upstream tag

1. Create a new branch from the upstream tag, for example `git checkout -b es81 vX.Y.Z`.
2. Re-add the one file `custom_components/ef_ble/eflib/devices/smart_meter_dual.py`.
3. Set `version` in `custom_components/ef_ble/manifest.json` to `X.Y.Z+es81.1`
   (bump the suffix for a fork-only change).
4. Tag and release as `vX.Y.Z-es81.1`.

## What differs

Nothing else differs from upstream: only the module above, the manifest `version`
and this file. The PR's manifest matcher and tests are not included.
