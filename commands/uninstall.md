---
description: 卸载额度状态栏(恢复默认状态栏)
---

卸载 Kimi Quota Statusline 插件:

1. 用 Bash 运行插件自带的跨平台卸载器:`python3 ~/.kimi-code/plugins/managed/kimi-quota-statusline/uninstall.py`(Windows 上为 `python uninstall.py`;macOS/Linux 也可用兼容壳 uninstall.sh)。若该路径不存在,查找插件当前所在目录下的 uninstall.py。
2. 卸载器会从 tui.toml 移除插件的 status_line command(先自动备份)。
3. 完成后提醒用户在 TUI 运行 /reload-tui 恢复默认状态栏。
