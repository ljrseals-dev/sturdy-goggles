# CLAUDE.md : AOC Magic Studio Standalone

Read `docs/CLAUDE_PROMPT.md` first; it is the full work plan and rules. Short version:
- Core is **numpy + stdlib only**. Evidence or it did not happen: run commands via `python audit/log.py cmd ... -- <command>`.
- Never skip/weaken tests, never hide failures, never claim what you cannot run (listening, browser, Windows/macOS).
- Consent gates stay; built-in synths are previews, never "realistic" or "cloned".
- Tests: `python tools/run_tests.py` (no pytest needed) or `pytest -q tests`. Build the one-file app: `python tools/build_pyz.py`.
- Slash commands in `.claude/commands/` run each phase.
