# Research Cycle

[Русский](README.ru.md)

Portable research skill: choose experiments, inspect results, revise the plan and
verify conclusions. The user defines goals, methods and resources. A target metric
and total wall deadline can be the only resource limits.

**Experimental v2.0.0-rc.2.** The adaptive Cheng pilot reached mean validation
macro-F1≥0.92 on three fresh training seeds in about2h29m.

| Historical run | Winner | Mean validation F1 | Mean held-out test F1 |
|---|---|---:|---:|
| Without skill | DenseNet121 | 0.902062 | 0.878772 |
| Adaptive with skill | DenseNet121 | **0.932217** | **0.886990** |

The test difference is **+0.822 percentage points**. This is an observational comparison
of different processes, not a controlled skill ablation. Epochs, recipes, stopping
rules and accounting differ. The patient-bootstrap interval includes zero; neither
a causal improvement nor compute/token savings is established.
[Report](docs/benchmarks/2026-11-cheng/REPORT.en.md) ·
[Metrics JSON](docs/benchmarks/2026-11-cheng/metrics.json) ·
[Seed CSV](docs/benchmarks/2026-11-cheng/seed_metrics.csv).

## Use

1. Download the [release](https://github.com/AegonnI/research-cycle/releases/tag/v2.0.0-rc.2)
   or expose `skills/research-cycle/` to your agent.
2. Define data/method boundaries, metric, confirmation and stopping objective.
   Use the [adaptive prompt](templates/ADAPTIVE_GOAL_TEMPLATE.en.md) for target+wall
   tasks, or the [full contract](templates/RESEARCH_TASK_TEMPLATE.en.md).
3. Let the agent choose models, parameters, epochs and subsequent experiments.
   Coverage quotas, attempt/compute caps and fixed reserves are optional user choices.
4. For Hermes explicitly invoke native `/goal`, use a real external deadline and
   verify results. Markdown cannot enable Goal or create execution tools.

SKILL.md is English; [guide.ru.md](skills/research-cycle/references/guide.ru.md) is the
Russian counterpart. Adaptive execution is bilingual. Load the relevant route/language.

## Execution

- **Adaptive reference executor:** [Cheng example](examples/cheng-adaptive/README.md),
  Linux/WSL and existing CUDA Python. Checks trials, allows longer-timeout retries,
  freezes recipes before three fresh seeds and closes on target or wall deadline.
  Executor source matches the audited pilot; a public setup wrapper is provided.
- **Standalone SQLite helper:** standard-library `memory.py` for explicitly bounded
  attempt/compute contracts. It records evidence but does not stop processes. For
  wall-only tasks use the adaptive executor instead of inventing extra resource caps.

The skill ZIP contains instructions/helpers/templates. The reference ZIP also contains
executor code, tests and aggregate evidence. Both exclude images, weights, experiment
databases, credentials and private manifests. See [limitations](docs/KNOWN_LIMITATIONS.md),
[usage](docs/USAGE.md), [Hermes](skills/research-cycle/references/hermes.md),
[attribution](THIRD_PARTY_NOTICES.md). [v1 history](docs/PILOT_ANALYSIS.ru.md) is preserved.

## Validate and build

```sh
python -m unittest discover -s tests -v
python scripts/build_release.py
```

Tests verify software behavior, not research efficacy. The skill requires no global
package installation; training libraries belong to the task. MIT; independent project.
