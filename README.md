# Kimi Quota Statusline

[中文独立文档](README.zh-CN.md) · [English version below](#english)

Kimi Code CLI 底部状态栏增强插件：把底部第一行替换为信息密集的彩色状态栏，额度数据**与 `/usage` 完全同源**（直连官方 `GET /coding/v1/usages` 接口）。

```
YOLO · K3·max [1M] · 5h ███░░░ 55% 1h25m · 7d █████░ 85% 12h25m · 37.6M ¥117.96 · pollen-project
```

进入 **swarm 模式**时，品牌蓝(`#4FA8FF`）水波自 `swarm` 标记处向两侧荡开，约 8 秒后收敛为静态品牌蓝标记：

```
YOLO · K3·max [1M] · swarm · 5h ███░░░ 58% 1h20m · 7d █████░ 85% 12h20m · 40.9M ¥125.15 · pollen-project
```

## 显示内容

| 段 | 内容 | 数据来源 |
|---|---|---|
| 权限模式 | `YOLO` / `AUTO` / `MANUAL`（大写，分色） | 状态栏 stdin 快照 |
| 模型·思考强度 `[上下文]` | `K3·max [1M]`，强度从当前会话 wire 日志重建 | wire.jsonl |
| swarm 特效 | 进入时品牌蓝水波双向扩散（~8s)，随后静态蓝标 | wire.jsonl `swarm_mode.*` |
| `5h` / `7d` 额度条 | 6 格进度条 + 已用百分比 + 重置倒计时，绿/黄/红三档 | **官方 `/usages` 接口**（超 10 分钟未更新压暗加 `~`，无数据不显示） |
| 本会话消耗 | token 量 + 估算金额（仅当前会话，不含其他会话） | 当前会话 wire.jsonl `usage.record` 聚合 |
| git 分支 / 项目目录 | ⎇ 分支、目录名 | stdin 快照 |

## 金额口径

按 Kimi 开放平台官方定价逐条累计（K3：输入 ¥20/百万 token、缓存命中 ¥2/百万、输出 ¥100/百万；缓存创建按标准输入价计）。是"等值估算"，套餐内实际不扣费。

## 安装

方式一（推荐，作为插件）:

```
/plugins install https://github.com/3209621-dotcom/kimi-quota-statusline
/kimi-quota-statusline:install
```

方式二（手动）:

```bash
git clone https://github.com/3209621-dotcom/kimi-quota-statusline.git
bash kimi-quota-statusline/install.sh   # 自动备份 tui.toml、写入 [status_line].command、kimi doctor 校验
# 然后在 TUI 运行 /reload-tui
```

要求：Kimi Code CLI ≥ 0.30.0(`[status_line]` 特性），Python 3,macOS / Linux。

## 卸载

```
/kimi-quota-statusline:uninstall   # 或手动 bash uninstall.sh
```

恢复官方默认状态栏。

## 工作原理

- `tui.toml` 的 `[status_line].command` 指向 `statusline.py`,TUI 每秒以内把 JSON 快照（模型/目录/git/权限/上下文用量/sessionId）喂给它，取 stdout 第一行渲染
- 思考强度与 swarm 状态：快照没有，从当前会话 `~/.kimi-code/sessions/*/<sessionId>/agents/main/wire.jsonl` 尾部记录重建
- token/金额：5h/7d 聚合全部会话 wire.jsonl 的 `usage.record`;"会话"段只聚合当前会话的 wire.jsonl（按文件 mtime 增量缓存；重活由 detached 后台进程刷新，状态栏单次运行 <50ms，远低于 300ms 预算）
- 额度百分比：官方 `GET https://api.kimi.com/coding/v1/usages`(Bearer 用本地 OAuth token，与 `/usage` 命令同源，见 kimi-code 仓库 `packages/oauth/src/managed-usage.ts`)；超过 10 分钟未更新压暗加 `~` 过期标记，从未拉到则不显示（本地 token 折算已于 v1.1.2 移除：与官方窗口非线性，校准漂移曾致误显）
- 动画帧率受 TUI 硬编码的 1 秒重跑间隔限制（`STATUS_LINE_RERUN_INTERVAL_MS`)，可配置化请求见 [issue #2396](https://github.com/MoonshotAI/kimi-code/issues/2396)

## 配置

- `KIMI_SL_NOCOLOR=1`：关闭 ANSI 颜色（纯文本）
- `statusline.py` 顶部常量：`PRICE_*`（定价）、`USAGES_URL`、`OFFICIAL_FRESH_S`（官方数据新鲜度阈值）、`BURST_S`（特效时长）

## License

[MIT](LICENSE)

---

<a id="english"></a>
<details>
<summary><b>English</b> (click to expand)</summary>

# Kimi Quota Statusline

A status line plugin for [Kimi Code CLI](https://github.com/MoonshotAI/kimi-code) (≥ 0.30.0). It replaces the footer's first line with a dense, colorful status bar whose quota data comes **straight from the official `GET /coding/v1/usages` endpoint — the same source as the built-in `/usage` command**.

```
YOLO · K3·max [1M] · 5h ███░░░ 55% 1h25m · 7d █████░ 85% 12h25m · 37.6M ¥117.96 · pollen-project
```

When **swarm mode** is entered, a brand-blue (`#4FA8FF`) water ripple spreads outward from the `swarm` marker for ~8 seconds, then settles back to a static brand-blue badge:

```
YOLO · K3·max [1M] · swarm · 5h ███░░░ 58% 1h20m · 7d █████░ 85% 12h20m · 40.9M ¥125.15 · pollen-project
```

## What it shows

| Segment | Content | Source |
| --- | --- | --- |
| Permission mode | `YOLO` / `AUTO` / `MANUAL` (uppercase, color-coded) | status line stdin snapshot |
| Model · effort `[context]` | `K3·max [1M]`; effort rebuilt from the session wire log | `wire.jsonl` |
| swarm effect | water-ripple burst on entry, then a static brand-blue marker | `wire.jsonl` `swarm_mode.*` |
| `5h` / `7d` quota bars | 6-cell bar + used % + reset countdown, green/yellow/red | **official `/usages` endpoint** (dimmed with a `~` marker when stale > 10 min; hidden when unavailable) |
| Current session usage | tokens + estimated cost (this session only) | current session's `wire.jsonl` `usage.record` aggregation |
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
- Token/cost figures: 5h/7d quota fallback aggregates `usage.record` entries across all session wire logs; the session figure aggregates only the current session's wire log. Cached per file mtime; heavy scans run in a detached refresher so the status line itself stays under ~50 ms (budget: 300 ms).
- Quota percentages come from the official `GET https://api.kimi.com/coding/v1/usages` (Bearer = local OAuth token — the exact endpoint `/usage` uses, see `packages/oauth/src/managed-usage.ts` in kimi-code). Values older than 10 minutes render dimmed with a `~` stale marker; when no official data has ever been fetched the bars are hidden. (The local token-based fallback was removed in v1.1.2: it is not linear with the official window and its calibration drifted, causing misleading readings.)
- Animation frame rate is bounded by the TUI's hardcoded 1 s rerun interval (`STATUS_LINE_RERUN_INTERVAL_MS`) — see [issue #2396](https://github.com/MoonshotAI/kimi-code/issues/2396) for the request to make it configurable.

## Configuration

- `KIMI_SL_NOCOLOR=1` — disable ANSI colors (plain text).
- Top-of-file constants in `statusline.py`: `PRICE_*` (token pricing), `USAGES_URL`, `OFFICIAL_FRESH_S` (official-data freshness threshold), `BURST_S` (effect duration).

## License

[MIT](LICENSE)

</details>
