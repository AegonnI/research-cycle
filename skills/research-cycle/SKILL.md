---
name: research-cycle
description: Conduct iterative computational research with user-defined goals, method boundaries, experiments, evidence and verification. Use for adaptive optimization, hypothesis testing and model comparisons.
---

# Research Cycle — 2.0.0-rc.2

The user supplies the question, permitted methods, resources and stopping objective.
Do not turn an example's numbers into universal quotas. Instructions are portable;
execution, native Goal and access permissions belong to the host environment.

For `execution_mode=adaptive_executor`, use [adaptive.md](references/adaptive.md)
(Russian: [adaptive.ru.md](references/adaptive.ru.md)) instead of the local SQLite
workflow. This requires compatible study tools; Markdown alone does not supply them.
For other Russian tasks use [guide.ru.md](references/guide.ru.md).

1. **Agree on success.** Fix metric, independent evaluation unit, data/split/evaluator,
   method boundaries and confirmation. A target and total wall deadline can be the
   only resource controls. Attempt counts, coverage minima, compute/token caps and
   fixed reserves apply only if explicitly requested. Document routine assumptions.
2. **Choose an appropriate next experiment.** Inspect current evidence, propose one
   experiment or a useful batch, measure results and revise the plan. Consider
   diversity and slower learners without requiring a fixed catalogue size. See
   [search.md](references/search.md) for architecture/model searches.
3. **Use the stopping objective.** `reach_target` stops at confirmed success or the
   declared deadline. `maximize_within_budget` continues its allocated search with
   planned confirmation/report time. Coverage gates and plateau rules are optional
   contractual choices. Do not burn resources merely to satisfy an invented quota.
4. **Keep evidence before launch.** Record configs, code/data identity, seeds, fidelity,
   failures, process time and artifacts. Use the supplied executor's ledger when it
   owns execution. The standalone [memory helper](references/memory.md) is for
   contracts with attempt/compute budgets; do not invent those caps for a wall-only task.
5. **Adapt execution too.** Estimate process deadlines from measured cost and chosen
   fidelity. A timeout is an execution outcome, not evidence of poor model quality.
   A repeat must permit changed operational timeouts while preserving scientific
   identity. If the tool cannot express it, report the interface blocker.
6. **Recover economically.** Save compact decisions/checkpoints after useful batches.
   After interruption read current state before recovery notes; reconcile open jobs.
   Resume does not reset the deadline. Unknown provider usage stays unknown.
7. **Confirm and freeze.** Freeze the recipe before fresh-seed confirmation. Include
   all prescribed seeds, preserve failures and do not reroll identical recipes to
   select lucky groups. Held-out evaluation follows frozen selection; no test tuning.
8. **Verify claims.** Recompute metrics from evidence and distinguish observations
   from hypotheses. Mechanistic explanations require a discriminating test; good
   validation does not establish absence of overfitting. Report reached, exhausted,
   inconclusive or invalid honestly. Native Goal judges do not prove scientific success.

For native `/goal` and clean comparisons see [hermes.md](references/hermes.md),
Russian [hermes.ru.md](references/hermes.ru.md). Activate native Goal only on request.
Deliver an auditable report, configs/code, trial table, evidence, costs and limitations.
Count actual structures separately from recipes/repeats. One run cannot establish
skill efficacy. Provenance/licenses: THIRD_PARTY_NOTICES.md in the distribution.
