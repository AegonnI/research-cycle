# Changelog

## v2.0.0-rc.2 — 2026-11-04 — adaptive pilot and public metrics

- Adaptive target+wall route; quotas, separate compute caps and fixed reserves are optional.
- RU/EN goal templates, data-driven next-experiment and timeout planning.
- Publish exact audited Cheng executor code with longer-timeout scientific retries,
  one frozen recipe/three fresh seeds, immutable accounting and automatic target/deadline closure.
- Public setup wrapper and software tests; no library installation or dataset/model bundling.
- Publish aggregate current/control metrics, per-seed CSV,14trial records and bilingual audit.
- Adaptive validation0.932217,test0.886990;historical control0.902062/0.878772.
  Observational comparison only:conditional test interval includes zero,causal benefit not established.
- Preserve v1 release and provenance. Release text generalizes the preparation fork;
  it has not itself been evaluated in another full agent search.

## v2.0.0-rc.1 — 2026-11-02 — local evaluation candidate

- Bilingual workflow/search/memory/Hermes guides and matched-run templates.
- Method boundaries, broad staged search and explicit stopping modes.
- Renamed-duplicate fix, declared scope checks, SQL leaders/stage filter, checkpoints and audit.
- Pinned selective MIT skill adaptations and retained notices.
- 16 ledger tests. No new training or skill-effect claims; v1.0.0 is unchanged.

## v1.0.0 — 2026-10-27

Initial public experimental release of the implementation used in the October 22 pilot.

- Portable `research-cycle` instructions and SQLite helper.
- Reusable goal/task template, usage instructions and ledger tests.
- Pilot analysis documenting successful operational threshold attainment and limits of the comparison.
- Documented configuration-fingerprint limitation and lack of technical held-out-data isolation.

The original three skill files are preserved byte-for-byte. No research-method or ledger bug fixes are included in this release. Native goal mode was not tested in the pilot. Fixes and further evaluation belong to a subsequent version.
