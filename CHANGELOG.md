# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与语义化版本。

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
