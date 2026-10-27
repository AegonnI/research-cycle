# Research Cycle v1.0.0 — experimental pilot baseline

The first public release packages a portable research skill, a Python standard-library SQLite ledger, and a reusable goal/task template.

## Included

- Original research-cycle 1.0 instructions, memory helper and reference, preserved from the evaluated pilot.
- Optional goal template and MIT license in the skill ZIP.
- Documentation, nine ledger tests, release builder and public aggregate pilot analysis in the repository.
- SHA256SUMS and a per-file release manifest.

## Pilot outcome

The skill-enabled run reached its operational validation target after the required confirmations. It stopped before exhausting the budget, as permitted by the target-reaching task. Native `/goal` was not activated. The pilot does not establish improved held-out quality, lower compute cost or reduced token consumption relative to the control.

## Known limitations

Changing `run_id` inside a configuration changes the duplicate-detection fingerprint. This release preserves and documents that behavior; the fix is deferred to the next iteration. Resource accounting and decision freeze are audit aids, not process watchdogs or technical test-data isolation.

See [README](https://github.com/AegonnI/research-cycle#readme), [known limitations](https://github.com/AegonnI/research-cycle/blob/v1.0.0/docs/KNOWN_LIMITATIONS.md) and [pilot analysis](https://github.com/AegonnI/research-cycle/blob/v1.0.0/docs/PILOT_ANALYSIS.ru.md).

This experimental release contains no patient-level data, trained models, experiment databases, conversation exports, credentials or private infrastructure manifests.
