# Kimi Quota Statusline

[中文文档](README.zh-CN.md)

A status line plugin for [Kimi Code CLI](https://github.com/MoonshotAI/kimi-code) (≥ 0.30.0). It replaces the footer's first line with a dense, colorful status bar whose quota data comes **straight from the official `GET /coding/v1/usages` endpoint — the same source as the built-in `/usage` command**.

```
YOLO · K3·max [1M] · 5h ███░░░ 55% 1h25m · 7d █████░ 85% 12h25m · 今日 37.6M ¥117.96 · pollen-project
```

When **swarm mode** is entered, a brand-blue (`#4FA8FF`) water ripple spreads outward from the `swarm` marker for ~8 seconds, then settles back to a static brand-blue badge:

```
YOLO · K3·max [1M] · swarm · 5h ███░░░ 58% 1h20m · 7d █████░ 85% 12h20m · 今日 40.9M ¥125.15 · pollen-project
```

## What it shows

| Segment | Content | Source |
| --- | --- | --- |
| Permission mode | `YOLO` / `AUTO` / `MANUAL` (uppercase, color-coded) | status line stdin snapshot |
| Model · effort `[context]` | `K3·max [1M]`; effort rebuilt from the session wire log | `wire.jsonl` |
| swarm effect | water-ripple burst on entry, then a static brand-blue marker | `wire.jsonl` `swarm_mode.*` |
| `5h` / `7d` quota bars | 6-cell bar + used % + reset countdown, green/yellow/red | **official `/usages` endpoint** (fresh ≤ 10 min, calibrated fallback) |
| Today's usage | tokens + estimated cost | `wire.jsonl` `usage.record` aggregation |
| git branch / directory | ⎇ branch, basename of cwd | stdin snapshot |

## Cost estimation

Per-token pricing follows Kimi's official open-platform rates (K3: input ¥20/M tokens, cached input ¥2/M, output ¥100/M; cache creation billed as standard input). It is an *equivalent* estimate — plan usage itself is not billed per token.

## Install

As a plugin (recommended):

```
/plugins install https://github.com/3209621-dotcom/kimi-quota-statusline
/kimi-quota-statusline:install
```

Or manually:

```bash
git clone https://github.com/3209621-dotcom/kimi-quota-statusline.git
bash kimi-quota-statusline/install.sh   # backs up tui.toml, writes [status_line].command, validates with kimi doctor
# then run /reload-tui in the TUI
```

Requirements: Kimi Code CLI ≥ 0.30.0 (the `[status_line]` feature), Python 3, macOS / Linux.

## Uninstall

```
/kimi-quota-statusline:uninstall    # or: bash uninstall.sh
```

Restores the built-in footer layout.

## How it works

- `[status_line].command` in `tui.toml` points at `statusline.py`. The TUI pipes a JSON snapshot (model, cwd, git branch, permission/plan mode, context usage, session id, version) on stdin, at most once per second, and renders the first stdout line.
- Thinking effort and swarm state are not in the snapshot; they are rebuilt from the current session's `~/.kimi-code/sessions/*/<sessionId>/agents/main/wire.jsonl` tail records.
- Token/cost figures aggregate `usage.record` entries across all session wire logs, cached per file mtime; heavy scans run in a detached refresher so the status line itself stays under ~50 ms (budget: 300 ms).
- Quota percentages come from the official `GET https://api.kimi.com/coding/v1/usages` (Bearer = local OAuth token — the exact endpoint `/usage` uses, see `packages/oauth/src/managed-usage.ts` in kimi-code). If the fetch fails (e.g. expired token), calibrated constants at the top of the script are used as fallback.
- Animation frame rate is bounded by the TUI's hardcoded 1 s rerun interval (`STATUS_LINE_RERUN_INTERVAL_MS`) — see [issue #2396](https://github.com/MoonshotAI/kimi-code/issues/2396) for the request to make it configurable.

## Configuration

- `KIMI_SL_NOCOLOR=1` — disable ANSI colors (plain text).
- Top-of-file constants in `statusline.py`: `PLAN_5H_LIMIT` / `PLAN_7D_LIMIT` (calibrated fallback when the official endpoint is unreachable), `PRICE_*` (token pricing), `USAGES_URL`, `BURST_S` (effect duration).

## License

[MIT](LICENSE)
