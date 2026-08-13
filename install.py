#!/usr/bin/env python3
"""kimi-quota-statusline 跨平台安装器:把 tui.toml 的 [status_line].command 指向本插件。

幂等;改动前自动备份(tui.toml.时间戳.bak);已有其他 command 会提示覆盖。
macOS / Linux 可用兼容壳 install.sh;Windows 直接 `python install.py`。
"""
import os
import re
import shutil
import subprocess
import sys
import time

SECTION_RE = r'(?ms)^\[status_line\]\n.*?(?=^\[|\Z)'


def build_command(target, os_name=None, executable=None):
    """生成 tui.toml 里的 command 行。
    posix 沿用 `python3 <路径>`;Windows 用解释器绝对路径,反斜杠按 TOML 规则双写转义。"""
    os_name = os_name or os.name
    if os_name == 'nt':
        exe = (executable or sys.executable).replace('\\', '\\\\')
        tgt = target.replace('\\', '\\\\')
        return f'command = "\\"{exe}\\" \\"{tgt}\\""'
    return f'command = "python3 {target}"'


def install(tui, target, os_name=None, executable=None, doctor=True):
    """把 [status_line].command 写入 tui(指向 target)。返回退出码。"""
    cmd_line = build_command(target, os_name, executable)
    text = open(tui, encoding='utf-8').read() if os.path.exists(tui) else ''

    if target in text or target.replace('\\', '\\\\') in text:
        print('已安装:[status_line].command 已指向本插件,无需变更')
        return 0

    if re.search(r'(?ms)^\[status_line\]\n(?:(?!\n\[).)*?^command\s*=', text):
        print('提示:[status_line].command 当前指向其他脚本,将被覆盖为插件版本(原文件已备份)')

    if os.path.exists(tui):
        shutil.copy(tui, f'{tui}.{time.strftime("%Y%m%d-%H%M%S")}.bak')

    if re.search(SECTION_RE, text):
        def repl(m):
            body = m.group(0)
            if re.search(r'(?m)^command\s*=', body):
                return re.sub(r'(?m)^command\s*=.*$', cmd_line, body, count=1)
            return body.rstrip('\n') + '\n' + cmd_line + '\n'
        text = re.sub(SECTION_RE, repl, text)
    else:
        if text and not text.endswith('\n'):
            text += '\n'
        text += f'\n[status_line]\n{cmd_line}\n'

    os.makedirs(os.path.dirname(tui), exist_ok=True)
    open(tui, 'w', encoding='utf-8').write(text)
    print(f'已写入: {tui}')

    if doctor and shutil.which('kimi'):
        r = subprocess.run(['kimi', 'doctor', 'tui', tui], check=False)
        if r.returncode != 0:
            return r.returncode
        print('kimi doctor 校验通过')
    return 0


def main():
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(plugin_dir, 'statusline.py')
    if not os.path.isfile(target):
        print(f'错误: {target} 不存在')
        return 1
    kc_home = os.environ.get('KIMI_CODE_HOME', os.path.expanduser('~/.kimi-code'))
    rc = install(os.path.join(kc_home, 'tui.toml'), target)
    if rc == 0:
        print('安装完成。在 Kimi Code TUI 中运行 /reload-tui 立即生效(或重开新会话)。')
        print('觉得好用的话,欢迎给个 Star ⭐ https://github.com/3209621-dotcom/kimi-quota-statusline')
    return rc


if __name__ == '__main__':
    sys.exit(main())
