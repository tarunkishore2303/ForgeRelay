# Task contract and commands

The runner requires a JSON object with id, kind (helper or tests), scope (unit), goal, target (one relative .py path), context, snapshot_paths, constraints, acceptance, baseline_commands and test_commands. All listed files resolve inside --project. Context entries are {"path":"module.py"}, optionally with inclusive 1-based start/end line ranges. Snapshot paths are explicit directories or files used to build an isolated copy; directories copy Python source only. List individual non-Python fixtures/config files explicitly if required. Do not include virtualenvs, dependency folders or secrets. The runner rejects symlink escapes and protected metadata paths.

Acceptance must include at least two observable behaviors. Test commands are arrays, never shell strings. They come from the primary agent's task, not the worker. Include independent acceptance tests in the snapshot and test_commands but omit them from context. Baseline commands run against the project before the model request; use the existing appropriate test suite. A baseline failure aborts dispatch.

Commands (prepend `python <skill-folder>/scripts/delegate.py`):

```text
doctor --smoke
run task.json --project D:/Projects/my-project
verify RUN_FOLDER --reviewed
repair RUN_FOLDER --feedback errors.txt
finish RUN_FOLDER --outcome accepted --reason "Independent checks and review passed" --review-minutes 1
finish RUN_FOLDER --outcome rejected --reason "Requires primary-agent redesign"
apply RUN_FOLDER --reviewed
report --project D:/Projects/my-project
```

Each request creates a new UUID run under PROJECT/.local-delegation/runs; old responses are not overwritten. It saves frozen baseline source, exact task/prompt, raw response, normalized proposal, status, compact metrics and test logs. Context-size estimation is a conservative character heuristic, not an exact tokenizer; split/reduce source if refused. `num_ctx` may be changed in the skill's assets/config.json or an explicit --config file. The runner does not change Ollama's global settings.

The worker returns only one Python file. Whole-file markdown fences are removed losslessly; other prose, truncation, syntax errors or excessive output are rejected. Import resolution and test assertion correctness still need review/tests. A candidate is an isolated directory, not a security sandbox. Run only code the primary agent has reviewed.

For reviewer fixes, edit RUN_FOLDER/candidate/TARGET, rerun verify, then finish accepted_with_changes. Verification records the exact candidate digest; apply refuses any later edit or changed baseline source. It backs up an existing target under the run directory. It never applies other candidate files. No parallel requests or unbounded retry loop are built in.

Use `finish --primary-usage-units NUMBER` only for observed usage in a consistent unit (for example, dashboard percentage points consumed in the same reset window). Include task preparation, review, repair and fallback. Local prompt/output counts are measured separately and are not a conversion to Codex subscription usage.
