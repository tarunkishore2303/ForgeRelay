# ForgeRelay

**Cloud judgment. Local drafting. Verified code.**

A Codex + Ollama experiment by Tarun Kishore.

A reusable local runner and Codex skill for small Python coding assignments. It calls your running Ollama service, needs only Python's standard library, and preserves each result separately. Default model: qwen2.5-coder:7b; context: 8192; output: 1200 tokens; at most one worker repair.

Read [WRITEUP.md](WRITEUP.md) for the experiment, economics and limits. [EVIDENCE.json](EVIDENCE.json) contains the summarized observed results. No subscription savings are claimed from local token counts.

## Use it now

From this directory:

```powershell
python delegate.py doctor --smoke
python -m unittest discover -s tests -v
python delegate.py report --project example-project
python economics.py estimate --scenario examples/conditional-savings.json
```

The example project already has an applied money-formatting helper produced through this workflow. Its first answer failed boolean validation, one local repair fixed it, and all eight project tests then passed. The original local run artifacts are excluded from this public repository; summarized measurements are in EVIDENCE.json.

## Install the skill in another project

```powershell
python D:/Projects/ForgeRelay/install.py --project D:/Projects/my-project
```

Use an existing project directory. This installs the self-contained skill under that project's .agents/skills/local-ollama-delegate.  In a Codex session opened in the selected project, invoke:

```text
$local-ollama-delegate Help implement this feature. Delegate only a small helper or a few tests, and verify before applying.
```

Codex discovers project skills; restart if changes do not appear. The installer does not alter other skill names or global configuration. Existing copies require --update, after inspection. This is a skills-only local plugin package; a remote server, account upload or MCP connector is unnecessary for this shell-based workflow. This repository publishes the source; it is not a marketplace submission.

## Prepare a task

Use examples/money-helper.json as a complete working contract. Change the target and requirements to match your feature. Read [task-contract.md](skills/local-ollama-delegate/references/task-contract.md).

```powershell
python delegate.py run my-task.json --project D:/Projects/my-project
```

The result contains a run folder. Read its proposal.py. After master code review:

```powershell
python delegate.py verify RUN_FOLDER --reviewed
python delegate.py finish RUN_FOLDER --outcome accepted --reason "Independent tests and review passed"
python delegate.py apply RUN_FOLDER --reviewed
```

Replace RUN_FOLDER with the exact returned path. --reviewed denotes the primary agent's code inspection, not a requirement to ask you again for routine authorized edits. If the tests fail, provide concrete feedback:

```powershell
python delegate.py repair RUN_FOLDER --feedback errors.txt
```

Review/verify the new run. One repair is allowed. For a trivial master correction, edit the candidate file, reverify, and finish accepted_with_changes. If larger redesign is needed, record rejected and let the primary agent implement it. Never apply unchecked worker output.

## Reproduce the demo on a fresh baseline

```powershell
python examples/bootstrap_demo.py --directory D:/Projects/ollama-fresh-demo
python delegate.py run examples/money-helper.json --project D:/Projects/ollama-fresh-demo
```

The bootstrap refuses to overwrite an existing directory. Independent money tests exist in the new demo, but the helper is absent. Follow the review/verify procedure. If bool validation fails, examples/money-feedback.txt contains the exact feedback used in the successful live repair.

## Usage accounting

`report` returns actual local tokens/time, outcomes and entered review/primary-usage values. Missing primary usage is reported with zero entries and null net savings. It does not read Codex's subscription dashboard. `finish --primary-usage-units N` records an observation in your chosen consistent unit; include preparation, review, repair and fallback in the comparison.

The calculator separates unchanged subscription fees, conditional allowance savings, entered extra-spend changes, local electricity estimates and elapsed time. Edit examples/measurement-template.json with real matched primary-only and hybrid measurements, then:

```powershell
python economics.py compare --measurement my-measurement.json
```

The template intentionally cannot produce a result until you enter measurements and confirm matching acceptance/usage conditions. The 10% result in conditional-savings.json is an illustration, not a prediction for your subscription.

## What the runner guarantees and what it does not

It checks baseline tests before dispatch, keeps source snapshots and artifacts within the selected project, validates syntax/output limits, executes only master-specified command arrays, requires explicit review before verification/application, backs up an overwritten target, refuses changed source or unverified candidate edits, and applies only one target file. It distinguishes accepted raw code from master-corrected code.

It currently emits one Python file and snapshots Python files in selected directories; list non-Python fixtures explicitly. It does not give the worker tools, automatically review code, measure this session's billed usage, install model weights, sandbox malicious Python, or guarantee net savings. Existing source fixtures and tests must fit the selected snapshot/context budget.

Relevant official documentation: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [subscription pricing and usage](https://learn.chatgpt.com/docs/pricing), [Ollama parameters](https://docs.ollama.com/modelfile).

## Results and related projects

Five full feature tasks passed 0/5 at both 16384 and 32768 context. A bounded helper passed eight tests after one local repair. These single trials do not establish a general success rate or measured subscription savings. See [the full experiment](WRITEUP.md).

Existing MIT-licensed projects cover related workflows: [Local Coding Agent](https://github.com/pvnc228/local-coding-agent), [delegate-local](https://github.com/IsmaelMartinez/delegate-local), and [rjv Codex/Ollama skills](https://github.com/rjvim/ai-skills). ForgeRelay records this experiment and provides a small Python-only runner; it does not claim to invent local delegation.

Licensed under MIT.
