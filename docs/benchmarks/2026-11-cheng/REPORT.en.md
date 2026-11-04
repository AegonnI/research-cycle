# Adaptive pilot and historical control — 4 November 2026

Public aggregate audit. No images, weights, patient identifiers/predictions, private
paths/manifests, chats or credentials are included. [Русский](REPORT.ru.md).

| Measure | Without skill | Adaptive with skill |
|---|---:|---:|
| Winner | DenseNet121 | DenseNet121 |
| Mean validation macro-F1 | 0.902062 | 0.932217 |
| Validation sample SD across3seeds | 0.010636 | 0.003614 |
| Mean held-out test macro-F1 | 0.878772 | 0.886990 |
| Test sample SD across3seeds | 0.006604 | 0.007433 |
| Confirmation epochs | 30 | 100 |
| AdamW learning rate | 0.0001 | 0.0001 |
| Weight decay | 0 | 0.0001 |
| Batch size | 64 | 32 |
| Main attempts | 68:63success/5failure | 14:14success |
| Trained architecture names | 32 | 8 |
| Accounted compute | 3094.83s+41.04stechnical | 8441.84s |
| Wall to verified closure | not established in this audit | 8918.24s |

Control failure/evaluation accounting was incomplete; the new executor measured full
process wall. Fewer attempts do not establish less compute. LLM usage is unknown.

Cheng2DMRI,3classes,160×160,randominit. Patient split: train1815slices/139patients,
validation668/47,test581/47,no overlap. The organizer evaluated only frozen winners
with identical FP32 test inference/preprocessing. No test inputs were supplied to agents.
Test had already been used in older pilots; no external independent dataset is available.

The new target was mean validationF1>=0.92 on3freshseeds within8h total wall,without
coverage/attempt/compute quotas or fixed reserves. The historical control received
a96attempt/4hcompute/8hwall task with coverage requirements. Stopping objectives differ.

The adaptive agent screened8models at50epochs,trained leaders longer,tested anotherLR,
then froze DenseNet121/AdamW/lr1e-4/wd1e-4/batch32/100epochs. Fresh seeds
1177536000/266497468/454566478 scored0.934492/0.928051/0.934110:mean0.932217.
All14jobs succeeded before deadline. Best validation checkpoints:epochs91/89/88.

Independent checks:SQLite integrity,47hash-chained events,14submitted/started/finished,
98artifact hashes,20sealed files,14CSVmetrics/histories/fingerprints,fresh-seed locking
and deadline. All3new checkpoints reproduced validation; an earlier organizer audit
also reproduced3historical winner checkpoints. No new training occurred during audit.
The nine [executor source files](../../../examples/cheng-adaptive/README.md) match
the pilot. Release guidance generalizes the evaluated preparation fork; no new full
agent run evaluated this edited release text. This is not a full data/weights release.

The test difference is **+0.822 percentage points**. Exploratory paired patient bootstrap:
47patients,5000replicates,seed20261104,conditional95%interval **[-2.182;+4.047]pp**,
including zero. This conditions on selected models/seeds,not full-search uncertainty
or a causal skill effect. Epochs,recipes,trainers,goals,coverage and accounting differ;
the historical LLM identity was not independently verified. One search per condition
cannot establish a skill benefit or resource savings. Matched repeated pairs are needed.

Historical control also had custom-scope violations,incomplete accounting and early
stopping with remaining budget. These limit process compliance but do not invalidate
its reproduced winner scores. Global architectural optimality is not established.

The adaptive run closed in about2h29m and wrote interpretation in2h30m. Its interactive
Hermes window then remained idle until the8h watchdog killed it. No trials were
submitted after closure. The agent's no-overfitting claim is unsupported:final-epoch
F1 was0.881747/0.925463/0.900530,below selected best scores. Mechanistic explanations
of architecture rankings remain untested. There were zero checkpoint events and one
report note; memory-recovery benefits were not shown. Hashes/tools/SQLtriggers do not
provide administrator-proof isolation.

[Metrics JSON](metrics.json) · [Seed CSV](seed_metrics.csv) · [14trial records](adaptive_trials.json).
