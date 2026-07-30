#!/bin/bash
# kimi-quota-statusline 卸载器:从 tui.toml 移除插件的 status_line command(自动备份)
set -e
PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
KC_HOME="${KIMI_CODE_HOME:-$HOME/.kimi-code}"
TUI="$KC_HOME/tui.toml"
[ -f "$TUI" ] || { echo "未找到 $TUI,无需卸载"; exit 0; }

python3 - "$TUI" "$PLUGIN_DIR" <<'PYEOF'
import os, re, shutil, sys, time

tui, plugin_dir = sys.argv[1], sys.argv[2]
text = open(tui).read()
if plugin_dir not in text:
    print('插件未安装(command 未指向本插件),无需变更')
    sys.exit(0)

shutil.copy(tui, f'{tui}.{time.strftime("%Y%m%d-%H%M%S")}.bak')

def repl(m):
    body = m.group(0)
    body = re.sub(r'(?m)^command\s*=\s*"python3\s+%s/statusline\.py"\n?' % re.escape(plugin_dir), '', body)
    # section 只剩表头则整体移除
    if not re.search(r'(?m)^[a-zA-Z_]+\s*=', body.split('\n', 1)[1] if '\n' in body else ''):
        return ''
    return body

text = re.sub(r'(?ms)^\[status_line\]\n.*?(?=^\[|\Z)', repl, text)
open(tui, 'w').write(text)
print(f'已从 {tui} 移除插件配置(备份已生成)')
PYEOF

if command -v kimi >/dev/null 2>&1; then
  kimi doctor tui "$TUI" && echo "kimi doctor 校验通过"
fi
echo "卸载完成。在 Kimi Code TUI 中运行 /reload-tui 恢复默认状态栏。"
