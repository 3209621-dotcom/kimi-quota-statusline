# 守成式维护方案设计 — 2026-08-07

## 背景

kimi-quota-statusline 已开源一周。数据:0 star、1 fork、近 14 天 38 个独立克隆(多数应来自 `/plugins install` 直接安装)。维护策略经讨论定为**守成为主**:不主动加功能,保证插件随 Kimi Code 演进持续可用。

## 目标

1. 发布积压的存量改动(v1.1.1),让用户能装到含最新修复的版本。
2. 把兼容性巡检流程固化为文档,之后每次 Kimi Code 更新照单执行,巡检成本降到最低。

非目标(YAGNI):不加新功能(路线图项继续留在想法池)、不做 README 营销/增长优化、不上 GitHub Action 自动化巡检。

## 设计

### 一、发布 v1.1.1

当前工作区未提交改动(已验证可用,见下):

- `statusline.py`:官方接口 User-Agent 由写死 `kimi-code-cli/0.30.0` 改为透传 stdin 快照的 `version` 字段(主进程 → detached refresh 进程),快照无该字段时回退裸 `kimi-code-cli`。
- `CHANGELOG.md` Unreleased 段两条:消耗统计由"今日全部会话"改为"当前会话";UA 动态化。
- `README.md` / `README.zh-CN.md`:对应双语同步(已改好)。

发布步骤(遵循 MAINTAINING.md 第六节):

1. 手动渲染测试 + 官方接口拉取测试复跑一遍,确认工作区状态可用。
2. `kimi.plugin.json` version `1.1.0` → `1.1.1`。
3. CHANGELOG:Unreleased 内容落定到 `## [1.1.1] - 2026-08-07`。
4. `git add -A && git commit && git push`。
5. 打 tag `v1.1.1` 并推送。

### 二、巡检清单入档

`docs/MAINTAINING.md` 新增一节"CLI 更新后的兼容性巡检",内容为本设计已验证的执行序列:

1. 读官方 changelog,找 status_line / 插件清单 / wire 日志 / 额度接口相关条目。
2. 检查 stdin 快照字段(`~/.kimi-code/statusline-stdin.json`):`model, cwd, gitBranch, permissionMode, planMode, maxContextTokens, sessionId, version`。
3. 检查当前会话 `wire.jsonl` 中 `usage.record` / `thinkingEffort` / `swarm_mode` 三类记录仍存在。
4. 拉一次 `GET /coding/v1/usages` 确认官方额度接口可用。
5. `kimi doctor tui` 校验配置;`cat ~/.kimi-code/statusline-stdin.json | python3 statusline.py` 手动渲染确认。
6. 若以上全部通过,只需更新 UA 之类的版本痕迹;若有失败项,按 MAINTAINING.md 数据通道节定位修复。

### 三、后续节奏

- 触发式维护:CLI 更新后照第二节清单巡检;用户 issue 随有随修。
- 路线图项(boosterWallet 余额段、per-model 定价等)继续留在 MAINTAINING.md 想法池,不主动实施。

## 验证

- 发布版在 GitHub 仓库可见(tag v1.1.1),`/plugins install` 装到的是 1.1.1。
- MAINTAINING.md 含巡检清单节,下次 CLI 更新可直接照用。

## 已验证的事实(设计依据)

- 2026-08-07 实测:CLI 0.31.1 下快照字段、wire 三类记录、官方接口、`kimi doctor tui`、手动渲染全部通过。
- 工作区改动已实测:主路径渲染正常,`fetch_official('0.31.1')` 拉取成功。
