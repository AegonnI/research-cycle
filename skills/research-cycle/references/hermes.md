# Hermes: native Goal and clean paired runs

The November4 adaptive pilot exercised native Goal and an external study executor
on Windows/WSL. See adaptive.md and the public benchmark report. A target+wall task
does not imply fixed coverage/compute/attempt gates. Use the current study status
after interruption; an interactive window can stay open after successful Goal closure.

Checked 2026-11-02: [goals](https://hermes-agent.nousresearch.com/docs/user-guide/features/goals),
[profiles](https://hermes-agent.nousresearch.com/docs/reference/profile-commands),
[memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory).
Check the installed version; ACP currently does not implement /goal.

The operator invokes `/goal <objective, contract path, acceptance and limits>` in
CLI/TUI. Reading a skill does not activate it. `/goal status` inspects progress;
pause/resume cannot reset study budgets. `goals.max_turns` counts continuation turns,
not all provider requests or tokens. Account main model, judge, compaction and retries.
Pin auxiliary.goal_judge to the same provider/model in both conditions, with no paid fallback.

Use an external watchdog for time/process limits. A native judge does not verify
scientific truth. If available, `/goal gate add <command>` requires a deterministic
command to exit successfully. A file-exists gate does not prove model quality. Never
change a gate or goal to relabel failure. Terminal budget exhaustion and threshold
attainment are separate outcomes. Disclose when evaluation is agent-reported rather
than independently verified.

Create two **new** profiles with `hermes profile create NAME --no-skills`, without
cloning, and two fresh workspaces/sessions. Set terminal.cwd explicitly; a profile
does not set the project directory. Only the experimental profile receives this skill.
Apply the following equally to the new profiles, merging rather than overwriting
personal configuration:

```yaml
memory:
  memory_enabled: false
  user_profile_enabled: false
  nudge_interval: 0
skills:
  creation_nudge_interval: 0
auxiliary:
  background_review:
    enabled: false
goals:
  max_turns: 40
```

Disable external memory/session-search, delegation, skill writing and automatic
project-skill discovery outside the explicit experimental skill, using controls
supported by the installed version. Check effective tools, skills and resolved model.
Do not inherit SOUL, old chats, previous trial outputs or preparation-repository
instructions. These settings are not OS file-access isolation.

Common task/data/runtime and model/provider/revision, reasoning, sampling, tools,
judge, budgets and stopping mode must match. The control may devise its own workflow
and use SQLite, but cannot read the experimental skill or previous studies. The common
task specifies outcomes/bounds, not a copy of the skill's algorithm. Run sequentially
on one GPU; randomize order before results. Record actual usage/deviations. One pair
is a feasibility pilot; repeated pairs are needed for skill-effect claims.
