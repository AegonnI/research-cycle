# Usage / Применение v2

For target+wall adaptive work start with the [EN prompt](../templates/ADAPTIVE_GOAL_TEMPLATE.en.md)
or [RU prompt](../templates/ADAPTIVE_GOAL_TEMPLATE.ru.md). The
[reference executor](../examples/cheng-adaptive/README.md) supplies the required MCP
study tools; a Markdown install does not create them. Its preparation wrapper copies
only supplied train/val inputs and uses an existing runtime. Configure a fresh profile.

The standalone memory.py below requires attempt/compute limits. It is a separate
execution option, not the wall-only adaptive implementation. Never invent extra quotas
solely to make a different helper accept the task. Unknown provider usage stays unknown.

Fill [the task contract](../templates/RESEARCH_TASK_TEMPLATE.en.md) before compute.
Русский [шаблон](../templates/RESEARCH_TASK_TEMPLATE.ru.md).
Detailed commands and config schema: [memory](../skills/research-cycle/references/memory.md),
[русская справка](../skills/research-cycle/references/memory.ru.md).
For model search: [search](../skills/research-cycle/references/search.md).
For native Hermes Goal and paired profiles: [Hermes](../skills/research-cycle/references/hermes.md).

No global installation or dependency downloads are required by the ledger. Use a new
v2 database, not an archived v1 study. Large evidence lives in files. Commands use
science/execution separation; code/data/seed/fidelity remain scientific influences.
Do not silently amend the supplied contract or use test metrics for selection.
Native goal activation, process deadlines and provider token quotas belong to the host.
