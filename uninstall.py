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

SECTION_RE = r'(?ms)^\[status_line\][ \t]*\r?\n.*?(?=^\[|\Z)'


def _write_atomic(path, text):
    """原子覆盖写:先写临时文件再替换,避免写一半崩溃留下截断的配置。"""
    tmp = path + '.tmp'
    open(tmp, 'w', encoding='utf-8').write(text)
    os.replace(tmp, path)


def _doctor(tui):
    """kimi doctor tui 校验。Windows 下 kimi 常是 npm 生成的 kimi.cmd shim,
    CreateProcess 无法直接执行 .cmd(抛 WinError 193),须经 cmd /c(shell=True)转一道;
    运行层面失败只提示不阻断——配置已写入,是否生效以 /reload-tui 实况为准。"""
    if not shutil.which('kimi'):
        return 0
    try:
        r = subprocess.run(['kimi', 'doctor', 'tui', tui],
                           check=False, shell=(os.name == 'nt'))
    except OSError:
        print('提示:kimi doctor 未能自动运行,运行 /reload-tui 观察状态栏是否生效即可')
        return 0
    if r.returncode != 0:
        return r.returncode
    print('kimi doctor 校验通过')
    return 0


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
        # 行级精确匹配:只删值里同时含插件目录与 statusline.py 的 command 行;
        # 注释或其他行里提及插件路径不算数(分隔符跟随写入平台,先归一化再比对)
        def is_ours(line):
            if not re.match(r'\s*command\s*=', line):
                return False
            v = line.split('=', 1)[1].replace('\\\\', '\\')
            return plugin_dir in v and 'statusline.py' in v
        body = '\n'.join(l for l in body.split('\n') if not is_ours(l))
        rest = body.split('\n', 1)[1] if '\n' in body else ''
        if not re.search(r'(?m)^[a-zA-Z_]+\s*=', rest):
            return ''  # section 只剩表头则整体移除
        return body

    text = re.sub(SECTION_RE, repl, text)
    _write_atomic(tui, text)
    print(f'已从 {tui} 移除插件配置(备份已生成)')

    if doctor:
        return _doctor(tui)
    return 0


def main():
    # Windows 控制台 stdout 默认 locale 编码(cp1252/GBK),中文提示会炸;强制 UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    kc_home = os.environ.get('KIMI_CODE_HOME', os.path.expanduser('~/.kimi-code'))
    rc = uninstall(os.path.join(kc_home, 'tui.toml'), plugin_dir)
    if rc == 0:
        print('卸载完成。在 Kimi Code TUI 中运行 /reload-tui 恢复默认状态栏。')
    return rc


if __name__ == '__main__':
    sys.exit(main())
