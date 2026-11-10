# Starting from your own words / Запуск своими словами

1. Give the agent the `research-cycle` skill folder or connect it using your host's
   skill mechanism. If the host cannot read files, supply SKILL.md and relevant guidance
   as text; full execution still depends on available tools.
2. Copy the [starter](../templates/RESEARCH_GOAL_TEMPLATE.en.md), then describe the task
   naturally. The agent uses [intake](../skills/research-cycle/references/intake.md) to
   produce a working task and proceeds; it asks only blocking questions.
3. Useful details: purpose/output, inputs/sources, known success criteria, method
   boundaries, desired deadline/resources, workspace/access and existing environment.
   These are hints, not mandatory form fields. A qualitative review needs no F1 threshold.

Русский: подключите навык, скопируйте [запускающий промпт](../templates/RESEARCH_GOAL_TEMPLATE.md)
и напишите задачу обычным языком. Агент сам оформит [рабочую постановку](../templates/RESEARCH_TASK_TEMPLATE.ru.md).
Если задано достаточно условий, отдельное утверждение заполненной формы не требуется.
Неизвестную цель исследования он должен уточнить, а не выбрать пример из репозитория.

The default workflow covers reviews, data analysis, simulations and computational
experiments. Existing tools may include search, files, code or a controller. Missing
capabilities must be reported. Markdown cannot grant access, enforce process deadlines
or activate native Goal. Do not invent unsupported flags or pretend strict timing.

Record format is task-dependent. The optional SQLite helper supports explicit
attempt/compute-budget contracts; see [memory](../skills/research-cycle/references/memory.md).
Use a supplied executor's ledger instead when it owns execution. The old Cheng MCP
example is retained in [v2.0.0-rc.2](https://github.com/AegonnI/research-cycle/tree/v2.0.0-rc.2/examples/cheng-adaptive),
not required by the universal skill. Host-specific notes are in the optional Hermes reference.

Reports should distinguish performed work from plans, findings from hypotheses and
measured usage from unknown values. Preserve user boundaries and fixed inputs.
Changing instruction text does not create new experimental evidence: benchmark
numbers remain historical and are not guarantees for another task.
