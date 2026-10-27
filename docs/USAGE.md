# Usage

## Host setup

Expose `skills/research-cycle/` to your existing agent environment. Follow that environment's installation instructions, or explicitly ask the agent to read the skill file. This repository does not install a global agent, a plugin marketplace, or a model runtime.

Copy and fill `templates/RESEARCH_GOAL_TEMPLATE.md` for your task. Keep the skill reusable; task-specific datasets, credentials, machine paths and metric thresholds belong in the private task contract.

The release ZIP has one top-level `research-cycle/` directory containing `SKILL.md`, `scripts/`, `references/`, an optional goal template under `assets/`, and the MIT license. The original skill instructions do not depend on that template; it is provided for the person preparing the task.

## Minimal ledger smoke test

From your new research workspace, create `contract.json`:

```json
{
  "question": "Compare candidate solutions under a fixed budget",
  "metric": {"key": "validation_score", "direction": "maximize", "target": 0.9},
  "max_attempts": 12,
  "max_compute_seconds": 3600,
  "final_evaluation_reserve_seconds": 120
}
```

Run the helper from the installed skill path:

```sh
python /path/to/research-cycle/scripts/memory.py init --db research.sqlite --contract contract.json
python /path/to/research-cycle/scripts/memory.py snapshot --db research.sqlite
```

Use the full workflow in [the memory reference](../skills/research-cycle/references/memory.md). The helper only uses Python's standard library. Your experiment trainer may require additional dependencies that this project neither bundles nor installs.

## Native goals

Where `/goal` is supported, explicitly invoke it with a measurable outcome, confirmation procedure and stopping limits. Refer to a filled task file for the full contract. See the [official Codex goal guide](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) for that host's behavior.

In another host, use its equivalent persistent-task feature if available. If none exists, disclose that the skill is running under an ordinary task instruction. Never claim native goal mode from the presence of a goal-shaped Markdown template.

## Interpreting completion

Separate these outcomes: target achieved under the contract; budget exhausted; inconclusive; invalid execution. A threshold-reaching task can stop before the budget is spent. If you want best attainable quality within a budget, say so explicitly instead of using a different stopping objective in the comparison group.

Do not use a test set for iterative target hunting. Freeze the choice before final evaluation and report validation success and held-out performance separately.
