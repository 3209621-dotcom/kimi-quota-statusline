# 守成式维护(v1.1.1 发布 + 巡检清单)实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 发布 v1.1.1(存量修复:消耗段改按会话统计、UA 动态化),并把 CLI 更新后的兼容性巡检清单固化进 MAINTAINING.md。

**Architecture:** 纯发布与文档操作,无新代码。工作区改动已齐备并实测通过,只需验证 → 版本落定 → 文档补节 → 推送打 tag。

**Tech Stack:** Python 3(零依赖)、git/GitHub(`gh` 已登录)、Keep a Changelog。

## Global Constraints

- 仓库:`https://github.com/3209621-dotcom/kimi-quota-statusline`,分支 `main`。
- 发布流程遵循 `docs/MAINTAINING.md` 第六节;提交信息沿用仓库风格(类型前缀 + 中文描述,如 `docs:`、`perf:`、`feat:`)。
- README 双语同步规则:任何行为变化必须 `README.md` / `README.zh-CN.md` 同步;本次两个文件的同步改动已在工作区,只需核对,不再新增内容。
- 版本号:`kimi.plugin.json` 的 `version` 由 `1.1.0` → `1.1.1`;tag 名 `v1.1.1`。
- 日期统一用 `2026-08-07`。

---

### Task 1: 发布前验证(工作区改动实测门禁)

**Files:**
- 无改动;只验证 `statusline.py` 工作区版本。

**Interfaces:**
- Consumes: 工作区全部未提交改动(`statusline.py`、`CHANGELOG.md`、`README.md`、`README.zh-CN.md`)。
- Produces: 验证通过结论,作为 Task 2 提交的前提。

- [ ] **Step 1: 手动渲染测试(彩色 + 纯文本两条)**

```bash
cd /Users/guo/Projects/kimi-quota-statusline
cat ~/.kimi-code/statusline-stdin.json | python3 statusline.py
cat ~/.kimi-code/statusline-stdin.json | KIMI_SL_NOCOLOR=1 python3 statusline.py
```

Expected: 两条都输出单行状态栏,含权限/模型/5h/7d/会话 token 金额段,无 traceback。

- [ ] **Step 2: 运行耗时必须远小于 300ms**

```bash
time (cat ~/.kimi-code/statusline-stdin.json | python3 statusline.py > /dev/null)
```

Expected: real 时间 < 0.3s(正常应 <0.1s)。

- [ ] **Step 3: 官方额度接口 + 动态 UA 实测**

```bash
python3 -c "
import statusline
d = statusline.fetch_official('0.31.1')
assert d and d.get('wk_limit'), 'official fetch failed'
print('OK', d.get('wk_used'), '/', d.get('wk_limit'))
"
```

Expected: 打印 `OK <used> / <limit>`(token 需在 15 分钟有效期内,CLI 运行中即有效;若失败先确认 `~/.kimi-code/credentials/kimi-code.json` 的 `expires_at` 未过期再重试)。

### Task 2: 版本落定并提交 v1.1.1

**Files:**
- Modify: `kimi.plugin.json`(第 3 行 `"version": "1.1.0"` → `"1.1.1"`)
- Modify: `CHANGELOG.md`(Unreleased 两条落定到 `## [1.1.1] - 2026-08-07`)
- 一并提交: `statusline.py`、`README.md`、`README.zh-CN.md`(工作区已有改动)

**Interfaces:**
- Consumes: Task 1 的验证通过结论。
- Produces: 本地 commit,`kimi.plugin.json` version = `1.1.1`;供 Task 4 推送。

- [ ] **Step 1: 改 `kimi.plugin.json` 版本号**

`"version": "1.1.0"` → `"version": "1.1.1"`

- [ ] **Step 2: 改 `CHANGELOG.md`**

把 `## [Unreleased]` 下整个 `### Changed` 块(两条)移到新标题下:

```markdown
## [1.1.1] - 2026-08-07

### Changed
- 消耗段由"今日"(全部会话当日聚合)改为"会话":token 与金额只统计当前会话的 wire.jsonl,不再跨会话总计
- 拉取官方额度接口的 User-Agent 版本号改为透传 CLI 快照的 `version` 字段,不再写死
```

`## [Unreleased]` 标题保留,其下清空。

- [ ] **Step 3: 核对 README 双语同步无遗漏**

```bash
git diff README.md | grep -c "^+.*Today's"        # 新增行残留旧文案数,期望 0
git diff README.zh-CN.md | grep -c '^+.*今日'      # 新增行残留旧文案数,期望 0
```

Expected: 两个 README 的 diff 均为"今日→会话 / Today's→Current session"的成对同步改动,新增行无旧文案残留。如发现遗漏,补同步后再继续。

- [ ] **Step 4: 提交**

```bash
git add statusline.py CHANGELOG.md README.md README.zh-CN.md kimi.plugin.json
git commit -m "chore(release): v1.1.1 — 消耗段改按会话统计,UA 版本动态化"
```

Expected: `git status --short` 干净;`git log --oneline -1` 显示该提交。

### Task 3: MAINTAINING.md 新增巡检清单节

**Files:**
- Modify: `docs/MAINTAINING.md`(插入新「七、CLI 更新后的兼容性巡检」,原七/八节顺延为八/九)

**Interfaces:**
- Consumes: 无(与 Task 2 独立,但提交顺序在后)。
- Produces: 本地 commit,维护文档含巡检清单。

- [ ] **Step 1: 在 `## 六、发布流程` 之后、`## 七、已知的坑(别再踩)` 之前插入新节,并把后两节标题改为八、九**

插入内容:

```markdown
## 七、CLI 更新后的兼容性巡检

Kimi Code 升级后(尤其跨 minor 版本),按本清单逐项核对;全部通过则无需改动,有失败项按「三、数据通道」定位修复。最近基线:CLI 0.31.1(2026-08-07 全部通过)。

1. **官方 changelog 对照**:https://www.kimi.com/code/docs/en/kimi-code-cli/release-notes/changelog.html ,搜 status_line / plugin / wire / usages 相关条目。
2. **stdin 快照字段**:`cat ~/.kimi-code/statusline-stdin.json` —— 应含 `model, cwd, gitBranch, permissionMode, planMode, contextUsage, contextTokens, maxContextTokens, sessionId, version`。
3. **wire 记录存在性**:对当前会话 `~/.kimi-code/sessions/*/<sessionId>/agents/main/wire.jsonl` 分别 `grep -c` `usage.record` / `thinkingEffort` / `swarm_mode`,均应 >0。
4. **官方额度接口**:`python3 -c "import statusline; print(statusline.fetch_official())"` 应返回含 `wk_limit` 的 dict(token 过期时返回 None,属预期回退,先确认 CLI 在线再判失败)。
5. **配置校验**:`kimi doctor tui`。
6. **手动渲染 + 计时**:`cat ~/.kimi-code/statusline-stdin.json | python3 statusline.py` 单行无报错;`time` 实测远小于 300ms。
```

同时:
- `## 七、已知的坑(别再踩)` → `## 八、已知的坑(别再踩)`
- `## 八、路线图(想法池)` → `## 九、路线图(想法池)`

- [ ] **Step 2: 核对全文无悬挂引用**

```bash
grep -n '^## ' docs/MAINTAINING.md
```

Expected: 一到九节顺序正确,无重复编号。

- [ ] **Step 3: 提交**

```bash
git add docs/MAINTAINING.md
git commit -m "docs: MAINTAINING 增加 CLI 更新兼容性巡检清单"
```

### Task 4: 推送、打 tag、远端验证

**Files:**
- 无文件改动;git 远端操作。

**Interfaces:**
- Consumes: Task 2、Task 3 的本地 commit,以及之前已提交的 spec commit(`ca3d417`)。
- Produces: origin/main 最新;tag `v1.1.1` 在 GitHub 可见。

- [ ] **Step 1: 推送 main**

```bash
git push origin main
```

Expected: 推送成功,无 non-fast-forward。

- [ ] **Step 2: 打 tag 并推送**

```bash
git tag v1.1.1 && git push origin v1.1.1
```

- [ ] **Step 3: 远端验证**

```bash
gh api repos/3209621-dotcom/kimi-quota-statusline --jq '.pushed_at'
gh api repos/3209621-dotcom/kimi-quota-statusline/tags --jq '.[].name'
git tag --list 'v1.1.1'
```

Expected: `pushed_at` 为当前时间;tags 含 `v1.1.1`。

- [ ] **Step 4: 最终核对**

```bash
git status --short && git log --oneline -4
```

Expected: 工作区干净;最近提交依次为 tag 指向的 v1.1.1 相关提交。
