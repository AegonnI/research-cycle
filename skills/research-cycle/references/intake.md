# From the user's words to a working research task

Use the current substantive task supplied by the user in the same message, an
explicitly linked preceding message or an identified attachment. The launch prompt,
this guide and repository examples are instructions/examples, not the research question.
If no actual task is supplied, ask for it; do not choose an old benchmark automatically.

Extract only supported information into this internal format:

| Field | Extract from the request |
|---|---|
| Question and purpose | What to find out and why |
| Deliverable and audience | Review, comparison, analysis, code, report; language/detail |
| Inputs and sources | Supplied files, datasets, sources and versions |
| Success and verification | Qualitative sufficiency or a named metric/target; appropriate checks |
| Methods and fixed conditions | Allowed/forbidden approaches, assumptions, evaluation rules |
| Resources and stopping | Only specified deadlines/cost/token/compute limits and stopping intent |
| Access and tools | Permitted reads/writes/workspace, existing runtime, optional manifest/tools |
| Unknowns | Blocking questions versus explicit provisional assumptions |

Preserve exact paths, numerical units, thresholds and permission boundaries. Do not
turn wishes into measured facts. If a supplied contract is fixed, reconcile the request
with it rather than overwriting it. The task document can use this structure or a
provided template; the user never has to fill placeholders manually.

Ask only what blocks safe/correct progress: a missing target column before training,
unavailable mandatory input, conflicting constraints, or an unresolved write location.
Group essential questions. Otherwise state reasonable assumptions briefly and proceed.
No numeric target, GPU, three seeds, SQLite, literature search or native Goal is
mandatory just because a previous example used it. A review can use source-based criteria.

Give a short operational interpretation, then perform the task with research-cycle.
When a writable workspace is authorized, save TASK.md or equivalent there; for a
conversation-only review, keep the interpretation in the response. Resolve relative
paths against the explicitly provided/current authorized workspace, never invent a
machine path. Do not read other chats/memory/projects to guess missing requirements.

Use already available tools according to the task. If execution/search/watchdog is
missing, state the actual capability limit and offer useful permitted work. Native
Goal is used only when requested and supported; mention does not activate the host.
Outputs can be literature evidence, data summaries, simulations or experimental
records; route to model-search/executor references only if relevant.
