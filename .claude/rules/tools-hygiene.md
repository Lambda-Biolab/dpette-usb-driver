# Tools Hygiene

- Experiment scripts go in `tools/`, one-off probing scripts in `tools/archive/`
- All hardware interaction scripts MUST log to `captures/`
- Follow the experiment process documented in `docs/EXPERIMENT_LOG.md`
- Never commit raw capture data (`.bin`, `.log` > 100KB) — reference by path only
