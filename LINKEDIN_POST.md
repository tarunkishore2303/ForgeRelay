Can a cloud coding agent save usage by handing smaller jobs to a local model?

I built ForgeRelay to test that idea: Codex handles planning, task contracts and review; a local Ollama model drafts bounded pieces of code.

The experiment used qwen2.5-coder:7b and a Python/SQLite workshop booking backend. We moved from small coding exercises to realistic assignments: pricing regression tests, cancellation rules, inventory reporting, idempotent checkout and FIFO waitlist promotion.

Every task had explicit interfaces, constraints, acceptance criteria and independent checks.

The results were humbling:

• None of the five full assignments passed unchanged at 16,384 context.
• Repeating them at 32,768 context still produced zero accepted full assignments.
• Total local generation time increased from about 367 to 455 seconds. These were single trials, so this is an observation—not a universal performance claim.

The useful result came from reducing scope. A small money-formatting helper failed a boolean edge case on its first attempt. Independent tests caught it. One precise feedback round let the local model repair it, and all eight example-project tests passed without a manual code fix.

That shaped ForgeRelay's reusable workflow:

Check the baseline → freeze relevant source → delegate one small task → review → run independent tests → allow one repair → apply the verified result or fall back.

The runner preserves attempts, limits scope, rejects stale source, backs up overwritten files and distinguishes local success from primary-agent corrections. It also includes a reusable Codex skill and usage-accounting tools.

My takeaway: task selection and verification matter more than simply increasing context. A failed delegation adds briefing and review to the implementation work you still need to do.

I also haven't demonstrated a savings percentage. With a ChatGPT/Codex subscription, reducing usage doesn't automatically reduce the fixed monthly fee. Any allowance benefit needs a matched comparison that includes preparation, review, repairs and fallback.

ForgeRelay is a small, reproducible experiment in finding where local models can earn their place in a coding workflow. Existing open-source projects already explore this space; this project shares our implementation, results and limits.

Code and full writeup: [GitHub URL will be inserted after publication]

What small coding tasks have your local models handled reliably—and how do you measure the review overhead?

#AIEngineering #LocalLLM #Ollama #Codex #SoftwareEngineering
