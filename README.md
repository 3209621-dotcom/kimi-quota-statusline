# Kimi Quota Statusline

Kimi Code CLI 底部状态栏增强插件:把底部第一行替换为信息密集的彩色状态栏,额度数据**与 `/usage` 完全同源**(直连官方 `GET /coding/v1/usages` 接口)。

```
YOLO · K3·max [1M] · 5h ███░░░ 55% 1h25m · 7d █████░ 85% 12h25m · 今日 37.6M ¥117.96 · pollen-project
```

swarm 模式激活时整行加边框特效 + swarm 反色高亮:

```
⟦ YOLO · K3·max [1M] ·  swarm  · 5h ███░░░ 58% 1h20m · 7d █████░ 85% 12h20m · 今日 40.9M ¥125.15 · pollen-project ⟧
```

## 显示内容

| 段 | 内容 | 数据来源 |
|---|---|---|
| 权限模式 | `YOLO` / `AUTO` / `MANUAL`(大写,分色) | 状态栏 stdin 快照 |
| 模型·思考强度 `[上下文]` | `K3·max [1M]`,强度从当前会话 wire 日志重建 | wire.jsonl |
| swarm 特效 | 整行 `⟦ ⟧` 品红边框 + 反色块(仅激活时) | wire.jsonl `swarm_mode.*` |
| `5h` / `7d` 额度条 | 6 格进度条 + 已用百分比 + 重置倒计时,绿/黄/红三档 | **官方 `/usages` 接口**(10 分钟内有效,失败回退本地校准值) |
| 今日消耗 | token 量 + 估算金额 | wire.jsonl `usage.record` 聚合 |
| git 分支 / 项目目录 | ⎇ 分支、目录名 | stdin 快照 |

## 金额口径

按 Kimi 开放平台官方定价逐条累计(K3:输入 ¥20/百万 token、缓存命中 ¥2/百万、输出 ¥100/百万;缓存创建按标准输入价计)。是"等值估算",套餐内实际不扣费。

## 安装

方式一(推荐,作为插件):

```
/plugins install <本仓库路径或 GitHub URL>
/kimi-quota-statusline:install     # 让 Agent 运行安装脚本并生效
```

方式二(手动):

```bash
bash install.sh     # 自动备份 tui.toml、写入 [status_line].command、kimi doctor 校验
# 然后在 TUI 运行 /reload-tui
```

要求:Kimi Code CLI ≥ 0.30.0(`[status_line]` 特性),Python 3(状态栏脚本),macOS / Linux。

## 卸载

```
/kimi-quota-statusline:uninstall   # 或手动 bash uninstall.sh
```

恢复官方默认状态栏。

## 工作原理

- `tui.toml` 的 `[status_line].command` 指向 `statusline.py`,TUI 每秒以内把 JSON 快照(模型/目录/git/权限/上下文用量/sessionId)喂给它,取 stdout 第一行渲染
- 思考强度与 swarm 状态:快照没有,从当前会话 `~/.kimi-code/sessions/*/<sessionId>/agents/main/wire.jsonl` 尾部记录重建
- token/金额:聚合全部会话 wire.jsonl 的 `usage.record`(按文件 mtime 增量缓存;重活由 detached 后台进程刷新,状态栏单次运行 <50ms,远低于 300ms 预算)
- 额度百分比:官方 `GET https://api.kimi.com/coding/v1/usages`(Bearer 用本地 OAuth token,与 `/usage` 命令同源);拉取失败时回退到脚本顶部的校准常量

## 配置

- `KIMI_SL_NOCOLOR=1`:关闭 ANSI 颜色(纯文本)
- `statusline.py` 顶部常量:`PLAN_5H_LIMIT` / `PLAN_7D_LIMIT`(官方接口不可用时的校准回退)、`PRICE_*`(定价)、`USAGES_URL`

## License

MIT
