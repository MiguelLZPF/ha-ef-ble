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
2. Re-add the module `custom_components/ef_ble/eflib/devices/smart_meter_dual.py`, its test
   `tests/eflib/test_smart_meter_dual.py`, and the three `ct2_l{n}_*` entries in
   `custom_components/ef_ble/sensor.py` (see What differs).
3. Set `version` in `custom_components/ef_ble/manifest.json` to `X.Y.Z+es81.1`
   (bump the suffix for a fork-only change).
4. Tag and release as `vX.Y.Z-es81.1`.

## What differs

Files that differ from upstream:

- `custom_components/ef_ble/eflib/devices/smart_meter_dual.py` (new)
- `tests/eflib/test_smart_meter_dual.py` (new)
- `custom_components/ef_ble/sensor.py`: three entries `ct2_l{n}_power`, `ct2_l{n}_current`,
  `ct2_l{n}_voltage` next to the `l{n}_*` Smart Meter entries (reuse the existing
  `port_*` translations, so no translation file changes)
- `custom_components/ef_ble/manifest.json`: `version` only
- `FORK.md` (this file)

The PR's manifest matcher is not included.

## Changelog

- 1.3.2+es81.2: CT2 per clamp (L1-L3 power, current, voltage, active flag) decoded from
  fields 985-996. Disabled by default; `pv_power_sum` (field 998) is unchanged.
