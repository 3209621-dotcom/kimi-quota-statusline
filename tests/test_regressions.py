#!/usr/bin/env python3
"""回归测试(无框架,直接 python3 tests/test_regressions.py):

1. 5h/7d 额度条只显示官方数据:过期加 ~ 压暗、本地折算不得再混入、无官方数据不显示
   (2026-08-09 修复:本地 token 折算与官方窗口非线性,校准漂移导致 5h 误显 90%+)
2. 长会话 wire.jsonl 中 swarm_mode.enter 跌出尾部 512K 窗口后仍能识别 swarm 状态
   (2026-08-09 修复:session_state 改为自文件尾向前分块扫描)
"""
import io
import json
import os
import sys
import tempfile
import time
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['KIMI_SL_NOCOLOR'] = '1'  # 纯文本,便于断言(须在 import 前设置)
import statusline

# Windows 控制台 stdout 默认 locale 编码(cp1252/GBK),中文用例名会炸;统一按 UTF-8 输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FAILED = []


def check(name, cond):
    print(('PASS' if cond else 'FAIL'), name)
    if not cond:
        FAILED.append(name)


def render(cache_obj):
    """用指定缓存渲染一次状态栏,返回输出文本。"""
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as f:
        json.dump(cache_obj, f)
    old_cache, old_stdin = statusline.CACHE, sys.stdin
    statusline.CACHE = path
    sys.stdin = io.StringIO(json.dumps({'sessionId': '', 'version': 'test'}))
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            statusline.main()
    finally:
        statusline.CACHE = old_cache
        sys.stdin = old_stdin
        os.unlink(path)
    return buf.getvalue()


def make_wire(size_kb, events):
    """造一个 wire.jsonl:events 在前,后面垫 noise 到 size_kb。返回 (sid, 文件路径)。"""
    tmp = tempfile.mkdtemp()
    statusline.SESSIONS = tmp
    sid = 'sess_test'
    d = os.path.join(tmp, 'wd_t', sid, 'agents', 'main')
    os.makedirs(d)
    p = os.path.join(d, 'wire.jsonl')
    pad = json.dumps({'type': 'noise', 'pad': 'x' * 1000}) + '\n'
    with open(p, 'w') as f:
        for ev in events:
            f.write(json.dumps(ev) + '\n')
        while os.path.getsize(p) < size_kb * 1024:
            f.write(pad)
    return sid, p


now = time.time()

# ---- Bug 1:额度条口径 ----
out = render({'ts': now, 'official': {'ts': now, 'h5_used': 4, 'h5_limit': 100,
                                      'wk_used': 27, 'wk_limit': 100}})
check('官方数据新鲜:显示 4%%,不带 ~', '4%' in out and '~4%' not in out)

out = render({'ts': now, 'h5': 44112427, 'd7': 152168064,
              'official': {'ts': now - 3600, 'h5_used': 4, 'h5_limit': 100,
                           'wk_used': 27, 'wk_limit': 100}})
check('官方数据过期:显示 ~4%% 过期标记', '~4%' in out)
check('官方数据过期:本地折算 93%% 不得混入', '93%' not in out)

out = render({'ts': now, 'h5': 44112427, 'd7': 152168064})
check('无官方数据:不显示 5h/7d 条', '5h' not in out and '7d' not in out)

# ---- Bug 2:长会话 swarm 识别 ----
enter = {'type': 'swarm_mode.enter', 'time': int(now * 1000)}
sid, _ = make_wire(600, [enter])
check('enter 跌出尾部 512K(600K 文件):仍识别 swarm', statusline.session_state(sid)[1] is True)

sid, _ = make_wire(10, [enter])
check('小文件 enter 在尾部:识别 swarm', statusline.session_state(sid)[1] is True)

sid, p = make_wire(600, [enter])
with open(p, 'a') as f:
    f.write(json.dumps({'type': 'swarm_mode.exit', 'time': int(now * 1000)}) + '\n')
check('enter 后已 exit:不显示 swarm', statusline.session_state(sid)[1] is False)

# 同一块内多条 swarm 记录:后者胜出(2026-08-09 曾误用行级门控,导致块内首条胜出)
exit_ = {'type': 'swarm_mode.exit', 'time': int(now * 1000)}
sid, _ = make_wire(10, [enter, exit_])
check('同块 [enter, exit]:不显示 swarm', statusline.session_state(sid)[1] is False)
sid, _ = make_wire(10, [enter, exit_, enter])
check('同块 [enter, exit, enter]:显示 swarm', statusline.session_state(sid)[1] is True)

# ---- Windows 适配(v1.2.0):detached 参数 / stdin UTF-8 / 跨平台安装器 ----
# A. detached 刷新进程的 Popen 参数按平台分支(Windows 用 DETACHED_PROCESS 防闪控制台窗口)
dk = statusline._detached_kwargs('posix') if hasattr(statusline, '_detached_kwargs') else None
check('posix:detached 用 start_new_session', dk == {'start_new_session': True})
dk = statusline._detached_kwargs('nt') if hasattr(statusline, '_detached_kwargs') else None
check('nt:detached 用 creationflags(DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP),无 start_new_session',
      isinstance(dk, dict) and 'start_new_session' not in dk
      and (dk.get('creationflags', 0) & 0x8) != 0 and (dk.get('creationflags', 0) & 0x200) != 0)


def render_bytes(stdin_bytes, cache_obj):
    """stdin 文本层故意用 ascii(模拟 Windows 非 UTF-8 locale):直接 .read() 必炸,正解是读 .buffer 按 UTF-8 解。"""
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as f:
        json.dump(cache_obj, f)
    old_cache, old_stdin, old_dbg = statusline.CACHE, sys.stdin, statusline.DEBUG_STDIN
    dbg = os.path.join(tempfile.mkdtemp(), 'stdin.json')
    statusline.CACHE, statusline.DEBUG_STDIN = path, dbg
    sys.stdin = io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding='ascii')
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            statusline.main()
    except Exception:
        pass
    finally:
        statusline.CACHE, statusline.DEBUG_STDIN = old_cache, old_dbg
        sys.stdin = old_stdin
        os.unlink(path)
    return buf.getvalue()


# B. stdin 文本层编码错误时仍按 UTF-8 解析;debug 快照写入也不得炸(中文路径)
snap_bytes = json.dumps({'sessionId': '', 'version': 't', 'cwd': 'D:/用户/项目'},
                        ensure_ascii=False).encode('utf-8')
out = render_bytes(snap_bytes, {'ts': now})
check('stdin 编码错误 locale:UTF-8 中文目录名正常显示', '项目' in out)

# D. stdout 是非 UTF-8 locale(模拟 Windows en-US 控制台 cp1252):输出强制 UTF-8,
#    否则中文目录名直接 UnicodeEncodeError,状态栏整行回退内置布局
fd, path = tempfile.mkstemp(suffix='.json')
with os.fdopen(fd, 'w') as f:
    json.dump({'ts': now}, f)
old_cache, old_stdin, old_stdout = statusline.CACHE, sys.stdin, sys.stdout
old_dbg = statusline.DEBUG_STDIN
statusline.CACHE = path
statusline.DEBUG_STDIN = os.path.join(tempfile.mkdtemp(), 'stdin.json')
sys.stdin = io.TextIOWrapper(io.BytesIO(snap_bytes), encoding='utf-8')
raw_out = io.BytesIO()
sys.stdout = io.TextIOWrapper(raw_out, encoding='cp1252')
try:
    statusline.main()
    sys.stdout.flush()
    cond = '项目'.encode('utf-8') in raw_out.getvalue()
except Exception:
    cond = False
finally:
    statusline.CACHE, statusline.DEBUG_STDIN = old_cache, old_dbg
    sys.stdin, sys.stdout = old_stdin, old_stdout
    os.unlink(path)
check('stdout 非 UTF-8 locale:输出强制 UTF-8(中文目录名不乱码)', cond)

# C. 跨平台安装器 install.py / uninstall.py
try:
    import install as _inst
    import uninstall as _uninst
except ImportError:
    _inst = _uninst = None
check('install.py / uninstall.py 可导入', _inst is not None and _uninst is not None)

if _inst:
    line_posix = _inst.build_command('/p/kimi-quota-statusline/statusline.py', os_name='posix')
    check('posix 命令行:python3 + 路径',
          line_posix == 'command = "python3 /p/kimi-quota-statusline/statusline.py"')
    line_nt = _inst.build_command('C:\\p\\kimi-quota-statusline\\statusline.py',
                                  os_name='nt', executable='C:\\Py\\python.exe')
    check('nt 命令行:解释器绝对路径 + TOML 转义',
          line_nt == 'command = "\\"C:\\\\Py\\\\python.exe\\" \\"C:\\\\p\\\\kimi-quota-statusline\\\\statusline.py\\""')

    # posix 安装 → 幂等 → 卸载往返
    home = tempfile.mkdtemp()
    tui = os.path.join(home, 'tui.toml')
    target = os.path.join(home, 'plugins', 'kimi-quota-statusline', 'statusline.py')
    os.makedirs(os.path.dirname(target))
    open(target, 'w').close()
    rc = _inst.install(tui, target, doctor=False)
    text = open(tui, encoding='utf-8').read()
    check('安装:写入 [status_line] 且 command 指向插件',
          rc == 0 and '[status_line]' in text and 'statusline.py' in text)
    _inst.install(tui, target, doctor=False)
    check('安装幂等:内容不变', open(tui, encoding='utf-8').read() == text)
    rc = _uninst.uninstall(tui, os.path.dirname(target), doctor=False)
    text = open(tui, encoding='utf-8').read()
    check('卸载:command 与空 section 一并移除',
          rc == 0 and 'statusline.py' not in text and '[status_line]' not in text)
    check('卸载生成 .bak 备份', any(f.endswith('.bak') for f in os.listdir(home)))

    # 覆盖已有 command:其他 section 不受影响
    home2 = tempfile.mkdtemp()
    tui2 = os.path.join(home2, 'tui.toml')
    open(tui2, 'w', encoding='utf-8').write('[status_line]\ncommand = "python3 /other/x.py"\n\n[editor]\n')
    _inst.install(tui2, os.path.join(home2, 'statusline.py'), doctor=False)
    text = open(tui2, encoding='utf-8').read()
    check('覆盖已有 command:其他 section 保留',
          'statusline.py' in text and '/other/x.py' not in text and '[editor]' in text)

    # Windows 形态:转义路径写入,卸载也能认出
    home3 = tempfile.mkdtemp()
    tui3 = os.path.join(home3, 'tui.toml')
    tgt3 = 'C:\\kc\\plugins\\kimi-quota-statusline\\statusline.py'
    _inst.install(tui3, tgt3, os_name='nt', executable='C:\\Py\\python.exe', doctor=False)
    check('nt 安装:命令行含转义反斜杠',
          '\\\\' in open(tui3, encoding='utf-8').read().split('command')[1])
    rc = _uninst.uninstall(tui3, 'C:\\kc\\plugins\\kimi-quota-statusline', doctor=False)
    check('nt 卸载:转义路径同样识别并移除',
          rc == 0 and 'statusline.py' not in open(tui3, encoding='utf-8').read())

print()
if FAILED:
    print(f'{len(FAILED)} 个用例失败')
    sys.exit(1)
print('全部通过')
