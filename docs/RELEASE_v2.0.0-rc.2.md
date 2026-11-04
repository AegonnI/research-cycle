Research Cycle v2.0.0-rc.2 adds adaptive research driven by a user-defined metric
target and total wall deadline. Mandatory architecture quotas and fixed reserves
are removed from the adaptive route. RU/EN prompts and a reference MCP executor
are included; retries can increase operational timeouts while preserving science.

The audited Cheng pilot reached validation macro-F1 **0.932217** on three fresh seeds
in about **2h29m**, using14successful attempts. Organizer test: **0.886990**, compared
with **0.878772** for the historical no-skill winner. Difference **+0.822pp**;
exploratory patient-bootstrap interval **[-2.182;+4.047]pp** includes zero.
Different recipes,epochs,goals and tools prevent causal skill-effect claims.

Адаптивный режим: цель и общий срок, без обязательных квот перебора. Новый результат
validation/test **0,932217/0,886990**, исторический без навыка **0,902062/0,878772**.
Это успешный пилот, а не доказанное преимущество навыка. В репозитории есть RU/EN-разбор,
JSON/CSV по seeds,14конфигураций и ограничения сравнения.

Assets:
- `research-cycle-v2.0.0-rc.2.zip`: portable skill, bilingual guidance and prompts.
- `research-cycle-reference-v2.0.0-rc.2.zip`: also executor code, setup, tests and aggregate evidence.
- `metrics.json`, `seed_metrics.csv`, `release-manifest.json`, `SHA256SUMS`.

35software tests and skill validation passed. The nine executor files match the
audited pilot; released guidance is generalized and was not evaluated in another
full agent run. No patient images/identifiers/predictions,weights,experiment databases,
credentials or private manifests are distributed. Existing runtime required; no
dependency installation is performed. Experimental prerelease; v1.0.0 remains unchanged.
