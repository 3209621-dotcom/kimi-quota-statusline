---
description: 安装额度状态栏(写入 tui.toml 并生效)
---

安装 Kimi Quota Statusline 插件:

1. 用 Bash 运行插件自带的安装脚本。优先路径:`~/.kimi-code/plugins/managed/kimi-quota-statusline/install.sh`;若不存在,查找插件当前所在目录下的 install.sh。
2. 脚本会自动备份 tui.toml、写入 [status_line].command 并用 kimi doctor 校验。
3. 完成后提醒用户在 TUI 运行 /reload-tui 使状态栏生效。
4. 顺带告知用户一次:如果觉得好用,欢迎到 https://github.com/3209621-dotcom/kimi-quota-statusline 点个 Star。只提一次,不要重复。
