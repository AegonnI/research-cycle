# Free model for the paired pilot

Public sources checked **2026-11-02**. Recommended cloud candidate: **Step 3.7 Flash
on Nous Portal's Free plan**. [Portal](https://portal.nousresearch.com/) lists a
$0.00/1M offering; [StepFun](https://github.com/stepfun-ai/Step-3.7-Flash) documents
agent support including Hermes. This leaves the training GPU free. Direct StepFun
API pricing is separate.

No public quota guarantee covers two long research sessions. Authenticate with
`hermes model`, choose the actual free catalogue entry and record its resolved ID,
provider and revision. Check account limits and a small tool-call preflight. The
suggested 300-request/4M aggregate-token allowance per condition includes judge,
compaction and retries; it is an experiment ceiling, not a promised provider quota.
Use identical smaller allowances if necessary, before either run. Disable paid
fallbacks and random model routers. Stop honestly on quota exhaustion.

API-quota-free fallback: local [qwen3.5:9b](https://ollama.com/library/qwen3.5:9b)
with tools via [Hermes' Ollama endpoint](https://hermes-agent.nousresearch.com/docs/guides/local-ollama-setup).
The Q4_K_M main weights are about 6.6GB, with additional context/runtime memory.
Reuse installed models first; this project does not download one. Quality for this
task is unvalidated. Use CPU inference or unload GPU-resident LLM weights during CNN
training, and widen wall limits equally before the pair.

[OpenRouter free limits](https://openrouter.ai/docs/api_reference/limits) without a
credit purchase are 50 requests/day and 20/minute; they cannot reliably cover two
long sessions. A free web chat is not a free agent API. Verify live terms before use.
