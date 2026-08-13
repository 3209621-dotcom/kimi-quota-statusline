# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与语义化版本。

## [Unreleased]

### Added
- `tests/windows-e2e.ps1` Windows 真机验收脚本:用本机真实 Node 照抄 TUI 的 `spawn(cmd.exe, ['/d','/s','/c', command])` 链路验证带引号路径解析、元字符路径(中文/空格/括号/&)压测、detached 刷新不闪窗(MainWindowHandle=0)、UTF-8 中文输出;CI windows job 接入(此前 TUI spawn 端到端链路零覆盖)

### Fixed
- Windows:`kimi doctor tui` 在 npm 安装的 `kimi.cmd` shim 下直接 CreateProcess 抛 WinError 193(OSError),`check=False` 拦不住,安装/卸载器会崩出 traceback——doctor 校验改经 `cmd /c`(shell=True)转一道并 `except OSError` 兜底只提示不阻断(回归 +2)

## [1.2.0] - 2026-08-13

### Added
- Windows 支持:后台刷新进程按平台分支(Windows 用 `DETACHED_PROCESS`,不再闪控制台窗口);stdin/stdout 强制 UTF-8(非 UTF-8 locale 下中文路径不再崩溃);跨平台安装器 `install.py` / `uninstall.py`(`install.sh` / `uninstall.sh` 保留为兼容壳)。注:TUI 真实拉起状态栏命令(带引号路径的解析、detached 不闪窗)在 Windows 真机上未做端到端验证,覆盖到 CI 冒烟为止
- 三平台 CI(`.github/workflows/ci.yml`):windows / ubuntu / macos 跑回归测试 + 中文路径冒烟渲染 + 安装/卸载往返
- README 顶部居中 hero 横幅(`assets/hero.svg`:品牌蓝渐变大标题 + 打字机轮换标语)+ 徽章行
- 安装完成后的一次性 Star 提示(安装器输出 + install 斜杠命令告知,只提一次)
- README 演示素材:状态栏静态截图 + swarm 水波动效 GIF(`assets/`,附生成器 make_demo.py)

## [1.1.2] - 2026-08-09

### Fixed
- 5h/7d 额度条弃用本地 token 折算回退(与官方窗口非线性,校准漂移导致 5h 误显 90%+):仅显示官方接口数据,超 10 分钟未更新压暗加 `~` 过期标记,无官方数据不显示
- swarm 标记在长会话中凭空消失:`swarm_mode.enter` 跌出 wire.jsonl 尾部 512K 扫描窗口;改为自文件尾向前分块扫描,取全文件最近一条 swarm_mode 记录(块内多条后者胜出)

### Added
- `tests/test_regressions.py` 回归测试(额度口径 4 例 + swarm 分块扫描 5 例)

## [1.1.1] - 2026-08-07

### Changed
- 消耗段由"今日"(全部会话当日聚合)改为"会话":token 与金额只统计当前会话的 wire.jsonl,不再跨会话总计
- 拉取官方额度接口的 User-Agent 版本号改为透传 CLI 快照的 `version` 字段,不再写死

## [1.1.0] - 2026-07-30

### Added
- swarm 模式动效：进入时品牌蓝(`#4FA8FF`,Kimi Code 官方主题 primary)水波自 `swarm` 标记向两侧扩散,约 8 秒后收敛为静态品牌蓝标记;双波干涉模拟水面质感
- 英文 README(README.md 切换为英文,中文移至 README.zh-CN.md)
- LICENSE(MIT)、CHANGELOG、issue/PR 模板、维护交接文档

### Changed
- 额度百分比优先使用官方 `GET /coding/v1/usages`(与 `/usage` 同源),10 分钟内有效;失败回退脚本内校准常量
- 金额按 K3 官方定价(输入 ¥20/M、缓存命中 ¥2/M、输出 ¥100/M)估算

## [1.0.0] - 2026-07-30

### Added
- 首个版本:权限模式 / 模型·思考强度 [上下文规格] / 5h·7d 额度条 / 今日 token 与金额 / git·目录
- 数据通道:TUI stdin JSON 快照 + 会话 wire.jsonl 重建 + 官方 usages 接口
- 安装/卸载脚本(install.sh / uninstall.sh,自动备份 + kimi doctor 校验)与插件斜杠命令
