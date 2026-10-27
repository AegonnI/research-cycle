# Research Cycle

[Русское описание](README.ru.md)

A portable agent skill for bounded computational research: measurable objectives, hypotheses, experiments, a SQLite research ledger, and evidence-backed conclusions.

**Status: experimental v1.0.0, an archived pilot baseline.** The skill and ledger are usable, but the pilot does not establish that they improve model quality, research efficiency, or token use. A known configuration-fingerprint limitation is documented below. This release preserves the tested implementation; improvements will be evaluated in a later version.

## What is included

```text
skills/research-cycle/
  SKILL.md                 Research instructions (Russian)
  scripts/memory.py        SQLite ledger; Python standard library only
  references/memory.md     Ledger commands and contract format
templates/
  RESEARCH_GOAL_TEMPLATE.md
docs/
  PILOT_ANALYSIS.ru.md     Pilot results, audit and methodological caveats
  KNOWN_LIMITATIONS.md     Confirmed limitations and next steps
tests/
  test_research_memory.py
```

The host agent supplies the language model, filesystem access, search and experiment execution. This project supplies a workflow and a small helper, not a standalone agent runtime. Installing it does not train a model or grant access to a GPU, external services or private files.

## Use the skill

1. Download `research-cycle-v1.0.0.zip` from [Releases](https://github.com/AegonnI/research-cycle/releases), or clone this repository and use `skills/research-cycle/`.
2. Put the skill folder in a location supported by your agent environment, or explicitly ask the agent to read `SKILL.md` and its referenced resources. Installation and discovery are host-specific; merely attaching a Markdown file does not guarantee automatic execution.
3. Fill in [the goal/task template](templates/RESEARCH_GOAL_TEMPLATE.md): question, metric, confirmation procedure, data, allowed changes and budgets.
4. Start a fresh research workspace. Tell the agent to use `research-cycle` and keep `research.sqlite` there. Keep previous research results outside its allowed inputs when evaluating independence.

In environments supporting `/goal`, explicitly invoke it with the filled objective. The skill does not activate native goal mode by itself. The pilot did **not** use native `/goal`.

See [usage](docs/USAGE.md) for a minimal ledger example. The instructions and templates in this release are primarily Russian; the Python command interface is English. No third-party Python packages are required for the ledger. Training dependencies belong to the selected research task.

## What the ledger does

- Registers hypotheses and training attempts before execution.
- Counts failed attempts and outstanding compute reservations.
- Stores metrics, findings and SHA-256 references to evidence files.
- Provides compact summaries for resuming research.
- Freezes decisions before a final evaluation and records the final outcome.

It does not independently establish scientific validity, terminate compute processes, enforce token limits, or prevent the same OS user from reading held-out labels. Use an external watchdog and, where needed, a separate evaluator.

## Pilot: 2D MRI architecture comparison

Two exploratory agent runs used the same patient-level split of the Jun Cheng dataset. Each selected ConvNeXt-Tiny, but their training recipes, seeds, initial preparation and stopping objectives differed.

| Measure | Without skill | With Research Cycle |
| --- | ---: | ---: |
| Mean validation macro-F1, three training seeds | 97.46% | 98.46% |
| Mean test macro-F1, three training seeds | 96.28% | 95.56% |
| Training attempts, including failures | 11 | 8 |
| Accounted compute-process time | 21.94 min | 35.07 min |

The skill run reached its predefined operational validation threshold and stopped after the required confirmations and final evaluation, before exhausting its budget. This was a target-reaching run, not an instruction to maximize quality until the budget ran out. Fewer attempts cannot automatically be interpreted as better search efficiency, and unused budget is not itself a failure.

The observed mean test difference was −0.72 percentage points; an exploratory paired patient-bootstrap interval included zero. This pilot provides an implementation check, not a controlled causal comparison of the skill. It does not measure the benefit of SQLite under context loss or show a token saving. Full analysis and all caveats: [PILOT_ANALYSIS.ru.md](docs/PILOT_ANALYSIS.ru.md).

## Known limitation in v1.0.0

The configuration fingerprint includes the complete supplied JSON. If it contains a `run_id`, changing that name changes the fingerprint even when scientific settings are identical. Renamed duplicates may therefore evade duplicate detection. Keep operational identifiers outside the scientific configuration where possible and review repeats manually. This release intentionally records the limitation instead of silently changing the audited implementation. See [all limitations](docs/KNOWN_LIMITATIONS.md).

## Development and release

Python 3.10+ is supported by the helper. Run:

```sh
python -m unittest discover -s tests -v
python scripts/build_release.py
```

The builder creates a ZIP with the skill, reusable goal template and MIT license, plus SHA-256 checksums. It uses an explicit file allowlist and does not package experiment databases, images, model weights, chat exports or machine configuration. The tests check ledger invariants; they do not demonstrate research efficacy or cover the known renamed-configuration limitation.

## Structure references

The packaging follows the folder-based convention used in [anthropics/skills](https://github.com/anthropics/skills) and [openai/skills](https://github.com/openai/skills). Format background: [Agent Skills specification](https://agentskills.io/specification). Those projects are references, not dependencies; this project is independent and is not endorsed by their maintainers.

## License

MIT. See [LICENSE](LICENSE). Dataset rights remain with their respective owners. This repository distributes no medical images or per-patient research outputs.
