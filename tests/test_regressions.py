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

print()
if FAILED:
    print(f'{len(FAILED)} 个用例失败')
    sys.exit(1)
print('全部通过')
