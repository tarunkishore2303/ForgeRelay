---
name: local-ollama-delegate
description: Delegate small coding tasks to local Ollama using exact source context and acceptance checks, record outcomes, and evaluate whether delegation reduces primary-agent usage. Use for a requested local delegation workflow; retain complex feature orchestration with the primary agent.
---

Use the bundled Python runner at `scripts/delegate.py`; it calls the user's existing Ollama service, without cloud API keys or dependencies. Read [the task contract](references/task-contract.md) when preparing an assignment.

Default to one helper or a few tests, one output file, 8192 context and a 1200-token output cap. The local qwen2.5-coder:7b experiment failed all complete feature assignments at both 16384 and 32768; a small promotion helper was useful after one import fix. This is evidence for the current model/setup, not a restriction on all local models. Use a larger context only when selected source needs it and verify offloading with `doctor`.

Before generation, run `doctor --smoke` and confirm the project's baseline checks pass. Create a task JSON with an exact API/behavior, required error/edge cases, constraints, acceptance criteria, explicit source files/ranges, a narrow snapshot and explicit test-command arrays. Avoid assigning work the primary agent already completed. Keep hidden evaluator tests out of source context. Select useful tests; generating many unverified tests is not progress.

Run `run TASK.json --project PROJECT`. Only a compact status is returned; full source and model answers stay in local artifacts. Read `proposal.py` and check imports, assertions, requirements and side effects before `verify RUN --reviewed`. Verification uses a frozen source copy and does not apply code to the project. A passing worker test alone is insufficient: add/run independent checks in the candidate, or use a task test command that includes master-authored evaluator tests.

One repair is available through `repair RUN --feedback FEEDBACK.txt`, with concrete errors and the same contract. Prefer direct correction for a trivial import error; record it as accepted_with_changes. After the repair budget, or when broader redesign is needed, complete the task with the primary agent. Do not keep sending failed broad assignments.

If verification passes, record `finish RUN --outcome accepted` or `accepted_with_changes` with a reason; rejected work gets `rejected`. Record review time and observed primary usage if available. `apply RUN --reviewed` applies only the verified target and refuses stale source. For a master correction, edit the candidate target, reverify, and record accepted_with_changes. Use the user's existing authorization for ordinary project edits; this flag denotes agent code review, not a new user permission request.

Run `report --project PROJECT` for outcomes, local tokens/time and manually entered primary usage. It cannot obtain this Codex session's subscription consumption automatically. Do not count local tokens as avoided cloud tokens, infer subscription bills from API prices, or claim savings without a primary-only comparison. For formulas and subscription-specific interpretation, read [economics](references/economics.md) and run `scripts/economics.py`.
