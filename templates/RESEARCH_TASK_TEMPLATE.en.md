# Research contract — fill once, keep identical across paired runs

Only fill resource controls the user requests. A target and total wall can suffice.
Coverage minima, attempt/compute/token caps and fixed reserves are optional; do not
turn blank fields into hidden restrictions. For target+wall use the adaptive template
and executor route. The standalone memory helper needs explicit attempt/compute limits.

- Question and output: [what is being compared; report/code/evidence]
- Goal mode: [reach_target OR maximize_within_budget]
- Primary metric/direction/unit: [e.g. validation macro-F1, maximize, patient-grouped split]
- Threshold and minimum coverage: [target optional for budget-maximizing mode]
- Fixed data/split/evaluator hashes and forbidden inputs: [...]
- Method boundaries: families [...]; architectures [...]; custom networks [yes/no];
  pretrained weights [...]; algorithms [...]; parameter ranges [...]; preprocessing [...].
- Fixed benchmark settings vs optimization variables: [...]
- Confirmation: finalists [...], seeds [...], fidelity [...], tie-break [...].
- Limits: attempts including failures [...]; compute [...]; wall [...]; total LLM tokens
  and provider requests including judge/retries [...]; download/storage [...].
- Reserves: confirmation [...], final evaluation [...], report [...].
- Stop: target+coverage+confirmation OR allocated search exhaustion, then finalization.
  Record unsuccessful/infeasible/invalid outcomes honestly. Resume does not reset limits.
- Environment manifest: [read-only path]; permitted runtime/cache/tool list [...].
- Writable root [...]; readable task/data paths [...]; isolated profile/session [...].
- Acceptance evidence: trial table, configs/code, predictions/metrics, coverage, costs,
  failures, reproducibility, uncertainty and limitations [...].
- Held-out evaluation: [independent organizer after frozen selection; access policy].

Use native `/goal` explicitly when supported. A goal judge is not a scientific evaluator.
For paired runs hold all fields/model/tools constant; only skill exposure differs.
