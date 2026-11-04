# Adaptive execution: target and total wall time

Use this route only with a compatible `study_*` executor. It owns execution, immutable
records and verification; do not run memory.py, SQL or a separate trainer alongside it.
Read study_info(details=true), task and contract. The user's metric/target, method
scope and total deadline control the run. No coverage or attempt quotas are implied.

Choose the next experiment from evidence. study_submit accepts one config or a batch;
study_wait/trials/trial expose outcomes, histories and logs. Epochs and operational
timeouts are planning choices. In the reference executor omitted timeout means the
remaining global wall, and study_retry can increase it without changing the science.
No mandatory screen/promote sequence or fixed confirmation-time reserve is required.

study_confirm freezes one recipe before generating fresh seeds. In the supplied
Cheng reference this means three independent trainings, with optional epochs chosen
before seed generation. All seeds count. If their mean is below target, return to
search and confirm a different recipe. Do not reroll the same recipe for lucky seeds.
Failed members can be retried with adjusted timeouts. Confirming seeds stay out of search.

Save compact checkpoints and decisions. On recovery read current study state first.
The controller closes on verified target or deadline; late results cannot qualify.
Technical closing/audit can finish later without extending research. Read the verified
numeric report and write interpretation separately. Unknown LLM usage remains unknown.
Host Goal is continuation machinery, not independent scientific verification.

Reference executor and setup (Linux/WSL, existing libraries, no bundled data):
https://github.com/AegonnI/research-cycle/tree/v2.0.0-rc.2/examples/cheng-adaptive
The example's 0.92, eight hours and 2D CNN constraints are benchmark choices, not
universal skill defaults. It provides code; a bare Markdown install provides no MCP server.
