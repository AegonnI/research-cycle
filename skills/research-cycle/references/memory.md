# SQLite ledger — standard library only

Use the existing Python. `MEMORY` means bundled `scripts/memory.py`. Evidence paths
cannot escape the database directory. Keep bulk arrays/weights outside SQLite.

```sh
python MEMORY init --db research.sqlite --contract contract.json
python MEMORY hypothesis --db research.sqlite --text "Claim/search question" --rationale "Reason" --test "Discriminating evidence"
python MEMORY begin --db research.sqlite --hypothesis 1 --config configs/trial.json --reserve-seconds 300
python MEMORY finish --db research.sqlite --experiment 1 --outcome completed --seconds 215 --metrics runs/1/metrics.json --evidence runs/1/train.log runs/1/train.py
python MEMORY finding --db research.sqlite --experiments 1 --text "Observation and limits" --hypothesis-status uncertain
python MEMORY checkpoint --db research.sqlite --note next.json
python MEMORY snapshot --db research.sqlite --stage confirm
python MEMORY show --db research.sqlite --table experiments --id 1
python MEMORY freeze --db research.sqlite --decision decision.json --evidence runs/1/model.pt evaluator.py
python MEMORY charge --db research.sqlite --seconds 20 --evidence evaluation.json
python MEMORY audit --db research.sqlite
python MEMORY close --db research.sqlite --status budget_exhausted
```

Required contract: `question`, `metric: {key, direction: maximize|minimize}`, positive
integer `max_attempts`, positive `max_compute_seconds`. Optional
`final_evaluation_reserve_seconds` protects final inference; reserve finalist training
in the controller too. Other rules and method_scope remain in the contract.

Recommended config:

```json
{
  "science": {
    "family": "residual_cnn", "architecture": "resnet18", "seed": 101,
    "fidelity": {"stage": "screen", "epochs": 3},
    "pretrained": false, "parameters": 11178051, "image_size": 160,
    "optimizer": "AdamW", "lr": 0.001, "batch_size": 32,
    "split_sha256": "REPLACE", "code_sha256": "REPLACE", "data_sha256": "REPLACE"
  },
  "execution": {"run_id": "screen-001", "output_dir": "runs/001"}
}
```

Put every scientific influence (including preprocessing, weight hashes and fidelity)
inside science. Only science plus the contract hash enter the fingerprint. With this
format no top-level fields except science/execution are allowed. Legacy flat configs
ignore only top-level run_id, output_dir, output_path, log_path, started_at. Renaming
stages/code solely to bypass duplicate detection is forbidden. An exact duplicate
requires a failed predecessor and --retry-reason; successful/running duplicates fail.
A fresh seed is a repeat, not a new architecture.

Completed trials require a finite numeric metric.key. Failed scores may be absent,
never invented zeroes. Evidence/metrics are hashed; use immutable per-trial trainer
snapshots, not one changing file. Open reservations survive context loss. Reconcile
processes before closing failed work. Overruns mark budget_violation, block new trials
and allow only settling work then closing invalid/stopped. charge accounts other
compute but does not enforce deadlines. Include validation/cleanup in process timeouts.

snapshot returns budget/counts, open trials, latest checkpoint, 20 recent hypotheses,
10 findings and five score leaders selected in SQL. Without --stage leaders may have
different fidelities and are not a final ranking. --stage confirm filters
science.fidelity.stage (legacy fidelity.stage too).
Checkpoint JSON: {"next_action":"...","reason":"...","evidence_ids":[1]}; max 12,000
characters. Save decisions and evidence references, not private reasoning.

freeze hashes the decision/evidence before held-out evaluation and blocks training.
audit checks trial/frozen files and fails on modifications, missing evidence or open
trials. It does not check metric correctness or goal attainment. close achieved needs
separate scientific verification, even after freeze. Other terminal states:
budget_exhausted, inconclusive, stopped, invalid.

This is an audit aid, not a security boundary/watchdog: no process termination, provider
token accounting, code inspection or test-label access prevention. Direct SQLite edits
can bypass it. Use a new database for v2; archived v1 databases are not migrated.
