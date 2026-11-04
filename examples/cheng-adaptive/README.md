# Cheng adaptive executor / Адаптивный исполнитель

Reference code used in the successful adaptive pilot: target mean validation macro-F1
0.92, total wall 8h, no coverage/attempt/compute quotas or fixed reserves. The nine
executor files are byte-identical to the audited pilot; hashes are in
EXECUTOR_SOURCE_HASHES.json. `prepare.py` is a public setup wrapper, not part of the
evaluated agent search. The portable release guidance generalizes the pilot route.

This example supports Linux/WSL (`fcntl` and process-group termination). Reuse an
existing CUDA Python with torch, torchvision and numpy; no packages are installed.
It requires prepared `images_fp16.npy` (N×160×160, [0,1]), `records.json` (index,
patient_id,label0..2,split=train/val) and `input_manifest.json`. No test rows.
No dataset, trained weights, private manifest or account settings are bundled.

```sh
python prepare.py --workspace /absolute/new-study --inputs-dir /absolute/prepared-trainval --runtime-python /absolute/existing/python
```

Run from this example directory, or pass its full path. The wrapper copies inputs,
checks patient separation, probes constructors and seals the workspace. It does not
start the wall clock or train MRI models. Supply `--manifest` for your own environment
inventory. An existing output folder is rejected; incomplete preparation is not deleted.

Configure a **fresh** host profile with only this MCP server, substituting paths:

```yaml
mcp_servers:
  research:
    command: /absolute/existing/python
    args: [-B, /absolute/new-study/executor/mcp_server.py, --root, /absolute/new-study]
    timeout: 180
    connect_timeout: 90
    tools: {resources: false, prompts: false}
```

For Windows-hosted Hermes, use `command: wsl.exe` and prepend
`[-d, YOUR_DISTRO, --, /absolute/existing/python, ...]` to args. Keep the workspace on
the desired Windows drive and use its `/mnt/...` view in WSL. Do not reuse personal
memory/history for an evaluation. The supplied [Hermes guide](../../skills/research-cycle/references/hermes.md)
describes the intended isolation; it is not an OS security boundary.

Immediately before starting the agent:

```sh
/absolute/existing/python -B /absolute/new-study/executor/operator_start.py --root /absolute/new-study
```

Then start Hermes with that profile, `--toolsets mcp-research`, the agent workspace
and a matching host wall budget. Set native turn ceilings high enough not to replace
your chosen time limit. Paste the [adaptive goal template](../../templates/ADAPTIVE_GOAL_TEMPLATE.en.md)
with concrete paths. Native `/goal` must be supported and explicitly invoked.

`study_confirm(trial_id, optional epochs, timeout_seconds)` creates three fresh-seed
trainings for one frozen recipe. A failed target can return to search. `study_retry`
accepts a larger operational timeout; omission uses remaining global wall. No seeds
may be cherry-picked or rerolled for the same recipe. `study_finalize` verifies the
target/deadline and writes `agent/report/verified_results.json`. Late results do not qualify.

The controller enforces process deadlines while connected. Disconnect stops active
work; resume preserves elapsed wall. An unresolved running record after a hard crash
requires operator reconciliation, not resetting/deleting attempts. Technical closing
can finish after the deadline without extending training. An interactive Hermes window
can remain open after Goal success; its later host-watchdog closure does not invalidate
an already closed study. LLM usage is not observed; use unknown, not zero.

Русский: подготовьте отдельную папку командой выше, укажите свой существующий Python
и train/val-входы. Настройте новый профиль только с MCP research, запустите operator_start
непосредственно перед Hermes и вставьте [русский промпт](../../templates/ADAPTIVE_GOAL_TEMPLATE.ru.md).
Числа0.92/8часов меняются параметрами `--target`/`--hours`. Рамки моделей и данных заданы
примером контракта; это стенд2DCNN, не универсальный NAS. Журналом владеет исполнитель.
Не переносите старые отчёты или test в папку агента. Публикуемые метрики — сравнение
исторических процессов, а не доказанный эффект одного навыка.
