# Research Cycle

[Русская инструкция](README.ru.md)

A skill for organizing research: understand the question, examine context, choose a
design, verify results and report conclusions. It covers literature reviews, data
analysis, simulations and method comparisons. Your agent host supplies execution tools.

## Start here

1. Give your agent the [research-cycle folder](skills/research-cycle), including
   `SKILL.md` and references, or connect it using the host's skill mechanism. With
   text-only access, supply SKILL.md and the relevant reference text.
2. Copy the [starter prompt](templates/RESEARCH_GOAL_TEMPLATE.en.md).
3. In the same message describe your task in your own words. No placeholders to fill.

The agent creates the working task, briefly states its interpretation and starts.
It asks only questions that block progress. A literature review needs no invented
numeric target or model training.

For example:

> I have hourly electricity consumption data in the project folder. Compare methods
> for forecasting the next day. You have two hours; use only installed libraries.
> Give me a report with an honest evaluation of forecast quality.

Or:

> Review methods for filling missing values in time series. Compare assumptions,
> limitations and the strength of available evidence. No training is needed.

## Useful details to mention

These are hints, not required form fields:

- What you want to learn and receive.
- Available files, data or sources.
- What would make the answer sufficient; a metric/target only if relevant.
- Allowed methods and fixed conditions.
- Desired deadline and other necessary resource limits.
- Permitted workspace and available tools/libraries.
- Report language, format and audience.

An environment manifest is optional. The [structured task template](templates/RESEARCH_TASK_TEMPLATE.en.md)
remains available and can be filled by the agent. SQLite, GPU, model quotas, fixed
reserves and a particular host are not defaults. Native Goal, search and technical
timeouts require actual host support; Markdown does not create them.

## Documentation and contents

- [Usage](docs/USAGE.md) and [capability limits](docs/KNOWN_LIMITATIONS.md).
- [Technical specification, Russian](docs/TECHNICAL_SPECIFICATION.ru.md): requirements for
  skill development, with/without-skill experiments, iterative improvement and verification.
- Skill and bilingual references in `skills/research-cycle/`.
- Optional SQLite helper and model-search guidance for applicable tasks.
- [Adaptation provenance and MIT notices](THIRD_PARTY_NOTICES.md).

Benchmark executor code and superseded setup guides were removed from the current
branch and retained locally. They remain available in the unchanged
[v2.0.0-rc.2 release](https://github.com/AegonnI/research-cycle/releases/tag/v2.0.0-rc.2).
Earlier releases and Git history are preserved. Current experimental version:
**2.1.0-rc.1**, [download](https://github.com/AegonnI/research-cycle/releases/tag/v2.1.0-rc.1).

## Validate and build

```sh
python -m unittest discover -s tests -v
python scripts/build_release.py
```

Tests cover helper behavior and consistency of published metrics. General instructions
do not establish reliable performance across every domain. No data, weights, private
settings or credentials are bundled. MIT licensed.

## Historical pilot results

These numbers are unchanged. They evaluate the previous adaptive Cheng route, not
the new free-form intake wording.

| Historical run | Winner | Mean validation F1 | Mean held-out test F1 |
|---|---|---:|---:|
| Without skill | DenseNet121 | 0.902062 | 0.878772 |
| Adaptive with skill | DenseNet121 | **0.932217** | **0.886990** |

Test difference: **+0.822 percentage points**. Epochs, recipes, stopping and accounting
differed; the conditional patient interval includes zero. A causal skill improvement
or resource saving is not established.
[Report](docs/benchmarks/2026-11-cheng/REPORT.en.md) ·
[Metrics JSON](docs/benchmarks/2026-11-cheng/metrics.json) ·
[Seed CSV](docs/benchmarks/2026-11-cheng/seed_metrics.csv).
