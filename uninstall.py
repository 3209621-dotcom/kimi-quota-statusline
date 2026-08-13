#!/usr/bin/env python3
"""kimi-quota-statusline 跨平台卸载器:从 tui.toml 移除插件的 status_line command(自动备份)。

macOS / Linux 可用兼容壳 uninstall.sh;Windows 直接 `python uninstall.py`。
"""
import os
import re
import shutil
import subprocess
import sys
import time

SECTION_RE = r'(?ms)^\[status_line\]\n.*?(?=^\[|\Z)'


def uninstall(tui, plugin_dir, doctor=True):
    """把指向 plugin_dir/statusline.py 的 command 从 tui 移除;空 section 一并删除。返回退出码。"""
    if not os.path.exists(tui):
        print(f'未找到 {tui},无需卸载')
        return 0
    text = open(tui, encoding='utf-8').read()
    # Windows 下文件里是 TOML 转义后的双反斜杠,两种形态都认
    if plugin_dir not in text and plugin_dir.replace('\\', '\\\\') not in text:
        print('插件未安装(command 未指向本插件),无需变更')
        return 0

    shutil.copy(tui, f'{tui}.{time.strftime("%Y%m%d-%H%M%S")}.bak')

    def repl(m):
        body = m.group(0)
        plain = body.replace('\\\\', '\\')  # TOML 转义归一化后再比对
        # 不用 os.path.join 拼完整路径:写入方的路径分隔符跟随写入平台,与当前平台无关
        if plugin_dir in plain and 'statusline.py' in plain:
            body = re.sub(r'(?m)^command\s*=.*\n?', '', body, count=1)
        rest = body.split('\n', 1)[1] if '\n' in body else ''
        if not re.search(r'(?m)^[a-zA-Z_]+\s*=', rest):
            return ''  # section 只剩表头则整体移除
        return body

    text = re.sub(SECTION_RE, repl, text)
    open(tui, 'w', encoding='utf-8').write(text)
    print(f'已从 {tui} 移除插件配置(备份已生成)')

    if doctor and shutil.which('kimi'):
        r = subprocess.run(['kimi', 'doctor', 'tui', tui], check=False)
        if r.returncode != 0:
            return r.returncode
        print('kimi doctor 校验通过')
    return 0


def main():
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    kc_home = os.environ.get('KIMI_CODE_HOME', os.path.expanduser('~/.kimi-code'))
    rc = uninstall(os.path.join(kc_home, 'tui.toml'), plugin_dir)
    if rc == 0:
        print('卸载完成。在 Kimi Code TUI 中运行 /reload-tui 恢复默认状态栏。')
    return rc


if __name__ == '__main__':
    sys.exit(main())
