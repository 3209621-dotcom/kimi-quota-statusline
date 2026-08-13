# 维护交接文档(MAINTAINING)

> 本文档面向本项目的后续维护者(包括未来的自己/新会话的 Agent),说明架构、数据通道、开发调试与发布流程。
> 读完这份文档即可独立维护,不需要原始会话上下文。

## 一、这个项目是什么

Kimi Code CLI(≥0.30.0)的底部状态栏插件。本体只有一个文件:`statusline.py`(Python 3,零依赖)。
通过 `tui.toml` 的 `[status_line].command` 接入 TUI:TUI 每秒(硬编码上限)把 JSON 快照喂给 stdin,取 stdout 第一行渲染到底部第一行。

- 仓库:https://github.com/3209621-dotcom/kimi-quota-statusline
- 本机项目目录(维护真源):`/Users/guo/Projects/kimi-quota-statusline`
- 最终用户的安装形态:`/plugins install` 后由 CLI 拷贝到 `~/.kimi-code/plugins/managed/kimi-quota-statusline/`,`install.sh` 把 command 指向那里的 statusline.py

## 二、文件地图

| 文件 | 作用 |
|---|---|
| `statusline.py` | 状态栏本体(全部逻辑) |
| `kimi.plugin.json` | 插件清单(name/version/interface/commands);**发布时记得升 version** |
| `install.py` / `uninstall.py` | 跨平台幂等安装器:备份 tui.toml → 写入/移除 `[status_line].command` → `kimi doctor tui` 校验;`install.sh` / `uninstall.sh` 仅为 macOS/Linux 兼容壳(一行 exec 调 .py) |
| `commands/*.md` | 插件斜杠命令(`/kimi-quota-statusline:install|uninstall`),body 是给 Agent 的提示词 |
| `README.md` / `README.zh-CN.md` | 首页 README.md 为中文内联 + 英文 `<details>` 折叠;zh-CN 为独立中文文件;**任何行为变化必须三处同步(README.md 中英两段 + zh-CN)** |
| `CHANGELOG.md` | Keep a Changelog 格式 |
| `tests/test_regressions.py` | 回归测试(无框架):额度口径 / swarm 分块扫描 / Windows 适配(detached 参数、stdio UTF-8、安装器行级匹配)共 28 例,`python3 tests/test_regressions.py` |
| `.github/workflows/ci.yml` | 三平台 CI(windows / ubuntu / macos):回归 + 中文路径冒烟渲染 + 安装/卸载往返 |
| `assets/` | `hero.svg`(README 顶部横幅:手写 SVG + SMIL 动画,品牌蓝渐变标题 + 三句打字机标语,改文案直接编辑;本地预览用 Chrome headless 截图)+ 演示素材 `statusline.png` / `swarm.gif` + 生成器 `make_demo.py`(依赖 Pillow,由 statusline.py 真实渲染逐帧生成;展示变化后重新跑一遍即可) |
| `docs/MAINTAINING.md` | 本文档 |

运行时产生的文件(在 `~/.kimi-code/`,不入库):
`statusline-tokens.json`(token/金额/官方额度缓存)、`statusline-stdin.json`(最近一次 stdin 快照,调试用)、`statusline-refresh.lock`(刷新锁)。

## 三、数据通道(改代码前必读)

1. **stdin 快照**(TUI → 脚本):`{model, cwd, gitBranch, permissionMode, planMode, contextUsage(0-1小数), contextTokens, maxContextTokens, sessionId, version}`。来源:`apps/kimi-code/src/tui/utils/status-line-command.ts`。
2. **会话 wire 日志**(`~/.kimi-code/sessions/*/<sessionId>/agents/main/wire.jsonl`,JSONL):
   - `config.update` / `llm.request` → 当前思考强度(`thinkingEffort`)
   - `swarm_mode.enter` / `swarm_mode.exit` → swarm 状态与进入时间(动效触发)
   - `usage.record` → token 消耗:`usage.{inputOther, output, inputCacheRead, inputCacheCreation}`,时间字段 `time`(epoch ms)
3. **官方额度接口**:`GET https://api.kimi.com/coding/v1/usages`,Bearer 用 `~/.kimi-code/credentials/kimi-code.json` 的 `access_token`(15 分钟有效期,CLI 运行时自动续)。返回 `usage`(周配额)+ `limits[]`(5h=300 TIME_UNIT_MINUTE),`used/limit` 为百分制。出处:kimi-code 仓库 `packages/oauth/src/managed-usage.ts`。
4. **额度显示口径**:仅用官方接口数据;超过 `OFFICIAL_FRESH_S`(600s)未更新压暗加 `~` 过期标记,从未拉到则不显示。本地 token 折算回退已于 v1.1.2 移除——与官方窗口非线性,校准漂移曾致 5h 误显 90%+(2026-08-09 用户报告),不要再加回来。

## 四、关键机制

- **增量缓存**:`refresh_cache()` 只扫当前会话 wire.jsonl(会话 token/金额)并拉官方额度;主流程发现缓存超过 `STALE_S`(20s)就 `Popen` 一个 detached `--refresh` 进程,自己用旧值先渲染 —— 状态栏永远 <50ms(预算 300ms)。
- **官方额度缓存**:`fetch_official()` 挂在 refresh 进程里,成功才覆盖,失败保留上次;超过 `OFFICIAL_FRESH_S`(600s)未更新则回退校准值。
- **swarm 动效**:`enter_ts` 来自最近一条 `swarm_mode.enter`,`elapsed < BURST_S`(8s)时整行走 `brand_flow()` 双波干涉水波;超时后只剩静态品牌蓝 `swarm` 段。重新进入会再次触发。
- **动画帧率上限**:TUI `STATUS_LINE_RERUN_INTERVAL_MS=1000` 硬编码,任何动效都是 1fps。已提 issue:[MoonshotAI/kimi-code#2396](https://github.com/MoonshotAI/kimi-code/issues/2396)(请求做成可配)。若未来官方放开,把 `brand_flow` 的速度参数调小即可变丝滑。

## 五、开发与调试

```bash
cd /Users/guo/Projects/kimi-quota-statusline
# 改 statusline.py 后,本机状态栏 1 秒内自动生效(tui.toml 指向本项目文件)

# 手动渲染测试(用最近一次真实快照):
cat ~/.kimi-code/statusline-stdin.json | python3 statusline.py
# 纯文本模式:
cat ~/.kimi-code/statusline-stdin.json | KIMI_SL_NOCOLOR=1 python3 statusline.py
# 强制重算 token 缓存:
python3 statusline.py --refresh
# 计时(必须远小于 300ms):
time (cat ~/.kimi-code/statusline-stdin.json | python3 statusline.py > /dev/null)
```

模拟 swarm 状态(不切换真实模式):在 `~/.kimi-code/sessions/wd_test_x/<sessionId>/agents/main/wire.jsonl` 写入伪造的 `swarm_mode.enter` 记录(time 用当前 epoch ms),stdin JSON 的 sessionId 指向它即可;测完删除 `wd_test_x`。

## 六、发布流程

1. 改代码 + 本地测试(上面清单 + `python3 tests/test_regressions.py` 回归测试);push 后确认三平台 CI 绿再发版。
2. 双语 README 同步;`CHANGELOG.md` 记录;`kimi.plugin.json` 的 `version` 升号。
3. `git add -A && git commit && git push`(origin = GitHub 仓库)。
4. 大版本可打 tag:`git tag v1.x.0 && git push --tags`。
5. 已安装的用户侧升级:`/plugins` 面板 Installed 页会有更新提示,Enter 更新;或重新跑 install 命令。

## 七、CLI 更新后的兼容性巡检

Kimi Code 升级后(尤其跨 minor 版本),按本清单逐项核对;全部通过则无需改动,有失败项按「三、数据通道」定位修复。最近基线:CLI 0.35.0(2026-08-12 全部通过;0.35.0 的 compaction token 计数修复只影响 ctx 读数,本插件不显示 ctx,无影响)。

1. **官方 changelog 对照**:https://www.kimi.com/code/docs/en/kimi-code-cli/release-notes/changelog.html ,搜 status_line / plugin / wire / usages 相关条目。
2. **stdin 快照字段**:`cat ~/.kimi-code/statusline-stdin.json` —— 应含 `model, cwd, gitBranch, permissionMode, planMode, contextUsage, contextTokens, maxContextTokens, sessionId, version`。
3. **wire 记录存在性**:对当前会话 `~/.kimi-code/sessions/*/<sessionId>/agents/main/wire.jsonl` 分别 `grep -c` `usage.record` / `thinkingEffort` / `swarm_mode`,均应 >0。
4. **官方额度接口**:`python3 -c "import statusline; print(statusline.fetch_official())"` 应返回含 `wk_limit` 的 dict(token 过期时返回 None,属预期回退,先确认 CLI 在线再判失败)。
5. **配置校验**:`kimi doctor tui`。
6. **手动渲染 + 计时**:`cat ~/.kimi-code/statusline-stdin.json | python3 statusline.py` 单行无报错;`time` 实测远小于 300ms。

## 八、已知的坑(别再踩)

- 官方额度接口是 `/usages`(**复数**),不是 `/usage`。
- access_token 只有 900s 有效期,不要在脚本里用 refresh_token 自己续(会顶坏 CLI 的凭据轮换);过期就回退校准值,等 CLI 续上自然恢复。
- `[status_line].command` 只接管底部**第一行**;第二行(原生 context 读数)是 `footer.ts` 写死的,关不掉,所以本插件不显示 ctx 条(避免重复)。
- 不要把耗时操作放进主流程(300ms 超时会被 SIGKILL,整行回退内置布局)——重活一律走 detached refresh。
- 多行输出无效:只有 stdout 第一行会被渲染。
- Windows:后台刷新 Popen 必须用 `DETACHED_PROCESS`(否则闪控制台窗口),POSIX 才用 `start_new_session`;stdin 快照走 `sys.stdin.buffer` 按 UTF-8 解,stdout 也要 `reconfigure(encoding='utf-8')`(控制台文本层可能是 GBK/cp1252,print 中文直接 UnicodeEncodeError);tui.toml 里 Windows 路径反斜杠按 TOML 双写转义,卸载匹配前先归一化(分隔符跟随写入平台,别用 `os.path.join` 拼路径来比对)。
- 安装/卸载器对 tui.toml 的匹配一律**行级精确**:只认 command 行的值;注释或其他行提及插件路径不算数(section 级宽松匹配会误删指向他人脚本的 command,v1.2.0 评审发现并修复)。CI 覆盖不到 TUI 真实 spawn command 的端到端解析(CI 无 kimi 环境),Windows 真机未验证,发版时需注明。

## 九、路线图(想法池)

- Extra Usage 钱包余额段(接口 `boosterWallet` 已返回,目前 STATUS_DISABLED 未启用)
- 并发会话段(接口 `parallel`:limit 30 + 活跃会话数)
- 官方若放开刷新间隔(issue #2396):动效改 10fps
- per-model 定价表(目前统一按 K3)
