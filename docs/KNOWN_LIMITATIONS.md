# Known limitations of v1.0.0

This is a record of the released implementation, not a claim that every planned improvement has been implemented.

## Configuration fingerprint includes operational names

`memory.py` hashes the entire configuration object. A `run_id` or output path inside that object changes the hash even if scientific settings are unchanged. This happened in the pilot retry after an infrastructure failure: the attempt was counted, but the renamed configuration did not require the explicit retry reason expected for an identical fingerprint.

Until fixed, keep operational IDs outside scientific configuration where possible and manually inspect repeats. A later version should separate scientific settings from operational metadata, preserve seed/data/code identifiers in the scientific hash, and add a regression test for differently named identical runs. The current tests do not cover that case.

## Memory utility has not been established

SQLite was used for hypotheses, attempts, resource accounting, findings and a final freeze. The pilot was one continuous research session, so it does not establish better recovery from context loss, fewer repeated hypotheses over long sessions, or reduced LLM token use. Token consumption was unavailable and must not be reported as zero.

## A numeric target is not a guarantee of generalization

The pilot reached its operational validation threshold and appropriately stopped after confirmation and final evaluation. It was not required to keep searching until it exhausted the budget. The held-out test score was lower than validation; this does not make the recorded threshold attainment false. Future comparisons must align stopping objectives as well as budgets.

## No technical enforcement boundary

The helper records reservations and checks supplied resource accounting; it does not stop processes. Use an external timeout that covers child processes. The agent can supply incorrect times or metrics, and a process with write access can modify SQLite or files directly. Hashes and the append-only event interface aid audit, not adversarial security. `close --status achieved` does not independently prove all scientific criteria.

Held-out labels should be evaluated by a separate process or account when strict isolation matters. Instructions to avoid a test file are not a filesystem permission boundary.

## Goal mode belongs to the host

The Markdown skill cannot enable `/goal` on its own. Neither pilot used native goal mode. Command support and token accounting depend on the host agent environment; do not assume identical integration across products.

## Avoid accidental writes into shared inputs

In the pilot, a dependency import wrote Python bytecode into a shared input folder. The original input hashes remained unchanged, and the event was disclosed. Set `PYTHONDONTWRITEBYTECODE=1` before the first import, or route bytecode caches into the run workspace. Strict read-only mounts are preferable where available.

## Experimental evidence is limited

The two exploratory runs used one patient-disjoint split, different seeds and different training recipes. One started with downloaded/prepared inputs and an installed additional library; the other performed that setup. Numerical differences cannot isolate the effect of the skill, SQLite, target-reaching instructions or native goal mode. The publicly shared analysis contains aggregate results only; it is not a complete independently reproducible dataset or trained-model release.
