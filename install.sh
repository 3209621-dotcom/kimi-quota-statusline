#!/bin/bash
# kimi-quota-statusline 安装器:把 tui.toml 的 [status_line].command 指向本插件
# 幂等;改动前自动备份(tui.toml.时间戳.bak);已有其他 command 会提示覆盖
set -e
PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$PLUGIN_DIR/statusline.py"
[ -f "$TARGET" ] || { echo "错误: $TARGET 不存在"; exit 1; }
KC_HOME="${KIMI_CODE_HOME:-$HOME/.kimi-code}"
TUI="$KC_HOME/tui.toml"

python3 - "$TUI" "$TARGET" <<'PYEOF'
import os, re, shutil, sys, time

tui, target = sys.argv[1], sys.argv[2]
cmd_line = f'command = "python3 {target}"'
text = open(tui).read() if os.path.exists(tui) else ''

if target in text:
    print('已安装:[status_line].command 已指向本插件,无需变更')
    sys.exit(0)

if re.search(r'(?ms)^\[status_line\]\n(?:(?!\n\[).)*?^command\s*=', text):
    print('提示:[status_line].command 当前指向其他脚本,将被覆盖为插件版本(原文件已备份)')

if os.path.exists(tui):
    shutil.copy(tui, f'{tui}.{time.strftime("%Y%m%d-%H%M%S")}.bak')

if re.search(r'(?ms)^\[status_line\]\n.*?(?=^\[|\Z)', text):
    def repl(m):
        body = m.group(0)
        if re.search(r'(?m)^command\s*=', body):
            return re.sub(r'(?m)^command\s*=.*$', cmd_line, body, count=1)
        return body.rstrip('\n') + '\n' + cmd_line + '\n'
    text = re.sub(r'(?ms)^\[status_line\]\n.*?(?=^\[|\Z)', repl, text)
else:
    if text and not text.endswith('\n'):
        text += '\n'
    text += f'\n[status_line]\n{cmd_line}\n'

os.makedirs(os.path.dirname(tui), exist_ok=True)
open(tui, 'w').write(text)
print(f'已写入: {tui}')
PYEOF

if command -v kimi >/dev/null 2>&1; then
  kimi doctor tui "$TUI" && echo "kimi doctor 校验通过"
fi
echo "安装完成。在 Kimi Code TUI 中运行 /reload-tui 立即生效(或重开新会话)。"
echo "觉得好用的话,欢迎给个 Star ⭐ https://github.com/3209621-dotcom/kimi-quota-statusline"
