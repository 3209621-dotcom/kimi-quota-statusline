#!/usr/bin/env python3
"""kimi-code 底部状态栏脚本(tui.toml [status_line].command)

stdin 收到 CLI 的 JSON 快照,stdout 替换底部状态栏(支持两行)。
运行预算 300ms,每秒最多一次 —— token 统计走缓存,重活由后台 detached 进程刷新。

第一行:权限 · 模型·强度 [上下文规格] · swarm · 上下文额度条 · 5h消耗 · 7d消耗
第二行:今日 token · 项目目录
- 5h/7d/今日消耗:本地会话 wire.jsonl 的 usage.record 按时间窗聚合(真实数据)
- 思考强度/swarm:当前会话 wire.jsonl 尾部记录重建
- ANSI 彩色;KIMI_SL_NOCOLOR=1 回退纯文本
"""
import glob
import json
import os
import subprocess
import sys
import time

HOME = os.path.expanduser('~/.kimi-code')
SESSIONS = os.path.join(HOME, 'sessions')
CACHE = os.path.join(HOME, 'statusline-tokens.json')
LOCK = os.path.join(HOME, 'statusline-refresh.lock')
DEBUG_STDIN = os.path.join(HOME, 'statusline-stdin.json')
STALE_S = 20        # 缓存超过 20s 触发后台刷新
LOCK_S = 60         # 刷新锁,避免并发刷新
TAIL_BYTES = 524288

# 套餐窗口总量(token):官方无接口,由 /usage 显示百分比 + 本地已用量反推校准
# (2026-07-30 校准:周 80% / 5h 34%;若套餐变更或长期漂移,按 /usage 重新校准)
PLAN_5H_LIMIT = 47428988
PLAN_7D_LIMIT = 689051201
WEEK_RESET_TS = 1785433833  # 周配额下次重置(epoch 秒),按 7 天周期自动顺延

# 官方额度接口(源码 packages/oauth/src/managed-usage.ts):GET {base}/usages,Bearer 认证
# 返回 usage(周配额)+ limits[](5h 等窗口)+ boosterWallet;used/limit 为百分制字符串
USAGES_URL = 'https://api.kimi.com/coding/v1/usages'
CRED_FILE = os.path.join(HOME, 'credentials', 'kimi-code.json')
OFFICIAL_FRESH_S = 600  # 官方数据 10 分钟内有效,过期回退校准值

# Kimi K3 官方定价(元/百万 token,2026-07 开放平台公示):
# 输入(未命中缓存)20、输入(缓存命中)2、输出 100;缓存创建按标准输入价计
PRICE_INPUT = 20.0
PRICE_OUTPUT = 100.0
PRICE_CACHE_READ = 2.0

USE_ANSI = os.environ.get('KIMI_SL_NOCOLOR') != '1'
RESET, BOLD, DIM = '\033[0m', '\033[1m', '\033[2m'
REVERSE = '\033[7m'

# swarm 动效:逐秒换帧(脚本无状态,帧号 = 当前秒数)
RAINBOW = [201, 165, 129, 93, 63, 39, 45, 51]  # 品红→紫→蓝→青 256 色循环
SPINNER = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'


def c256(text, n, *extra):
    if not USE_ANSI:
        return text
    return f'\033[38;5;{n}m' + ''.join(extra) + str(text) + RESET
CYAN, GREEN, YELLOW, RED, MAGENTA, BLUE, GRAY = (
    '\033[36m', '\033[32m', '\033[33m', '\033[31m', '\033[35m', '\033[34m', '\033[90m')


def c(text, *codes):
    if not USE_ANSI or not text:
        return text
    return ''.join(codes) + str(text) + RESET


def sep():
    return c(' · ', DIM)


def fmt_tokens(n):
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    if n >= 1_000:
        return f'{n / 1_000:.1f}K'
    return str(n)


def fmt_ctx(n):
    """上下文规格:1024 进制,1048576→1M,262144→256K。"""
    if n >= 1048576:
        return f'{n / 1048576:g}M'
    return f'{round(n / 1024)}K'


# ---------- token 聚合 + 官方额度(后台刷新进程执行) ----------
def fetch_official():
    """拉官方额度:周配额(usage)+ 5h 窗口(limits[])。token 过期或失败返回 None。"""
    import urllib.request
    try:
        cred = json.load(open(CRED_FILE))
        if cred.get('expires_at', 0) < time.time() + 10:
            return None
        req = urllib.request.Request(USAGES_URL, headers={
            'Authorization': f"Bearer {cred['access_token']}",
            'Accept': 'application/json', 'User-Agent': 'kimi-code-cli/0.30.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
        out = {'ts': time.time()}
        wk = d.get('usage') or {}
        if wk.get('limit'):
            out['wk_used'] = float(wk.get('used', 0))
            out['wk_limit'] = float(wk['limit'])
            out['wk_reset'] = wk.get('resetTime', '')
        for item in d.get('limits') or []:
            w = item.get('window') or {}
            if w.get('duration') == 300 and w.get('timeUnit') == 'TIME_UNIT_MINUTE':
                det = item.get('detail') or {}
                if det.get('limit'):
                    out['h5_used'] = float(det.get('used', 0))
                    out['h5_limit'] = float(det['limit'])
                    out['h5_reset'] = det.get('resetTime', '')
        return out if len(out) > 1 else None
    except Exception:
        return None


def refresh_cache():
    now_ms = int(time.time() * 1000)
    lt = time.localtime()
    t_today = int(time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1)) * 1000)
    t_5h = now_ms - 5 * 3600 * 1000
    # 周窗口对齐套餐重置周期(非滚动 7 天)
    reset = WEEK_RESET_TS
    while time.time() > reset:
        reset += 7 * 86400
    t_week = int((reset - 7 * 86400) * 1000)
    today = h5 = d7 = 0
    today_cost = h5_cost = d7_cost = 0.0
    for root, _dirs, names in os.walk(SESSIONS):
        if 'wire.jsonl' not in names:
            continue
        p = os.path.join(root, 'wire.jsonl')
        try:
            if os.stat(p).st_mtime * 1000 < t_week:
                continue
            with open(p, 'rb') as f:
                for line in f:
                    if b'usage.record' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    if rec.get('type') != 'usage.record':
                        continue
                    t = rec.get('time', 0)
                    if t < t_week:
                        continue
                    u = rec.get('usage', {})
                    s = (u.get('inputOther', 0) + u.get('output', 0)
                         + u.get('inputCacheRead', 0) + u.get('inputCacheCreation', 0))
                    cost = (u.get('inputOther', 0) * PRICE_INPUT
                            + u.get('output', 0) * PRICE_OUTPUT
                            + u.get('inputCacheRead', 0) * PRICE_CACHE_READ
                            + u.get('inputCacheCreation', 0) * PRICE_INPUT) / 1e6
                    d7 += s
                    d7_cost += cost
                    if t >= t_today:
                        today += s
                        today_cost += cost
                    if t >= t_5h:
                        h5 += s
                        h5_cost += cost
        except OSError:
            continue
    tmp = CACHE + '.tmp'
    # 官方额度:拉取成功则更新,失败保留上次结果
    official = fetch_official()
    if official is None:
        try:
            official = json.load(open(CACHE)).get('official')
        except Exception:
            official = None
    try:
        with open(tmp, 'w') as f:
            json.dump({'ts': time.time(), 'today': today, 'h5': h5, 'd7': d7,
                       'today_cost': today_cost, 'h5_cost': h5_cost, 'd7_cost': d7_cost,
                       'official': official}, f)
        os.replace(tmp, CACHE)
    except OSError:
        pass
    try:
        os.remove(LOCK)
    except OSError:
        pass


def load_tokens():
    """读缓存;过期则 detached 刷新,当前用旧值先显示。"""
    try:
        cache = json.load(open(CACHE))
    except Exception:
        cache = None
    stale = not cache or (time.time() - cache.get('ts', 0)) > STALE_S
    if stale:
        try:
            if not os.path.exists(LOCK) or time.time() - os.stat(LOCK).st_mtime > LOCK_S:
                open(LOCK, 'w').close()
                subprocess.Popen([sys.executable, os.path.abspath(__file__), '--refresh'],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        except OSError:
            pass
    return cache or {}


def reset_hint(iso):
    """ISO 时间 → 紧凑倒计时:13h / 2h14m / 48m。"""
    if not iso:
        return ''
    try:
        from datetime import datetime
        ts = datetime.fromisoformat(iso.replace('Z', '+00:00')).timestamp()
        s = int(ts - time.time())
        if s <= 0:
            return ''
        d, s = divmod(s, 86400)
        h, s = divmod(s, 3600)
        m = s // 60
        if d:
            return f'{d}d{h}h'
        if h:
            return f'{h}h{m}m' if m else f'{h}h'
        return f'{m}m'
    except Exception:
        return ''


def session_state(session_id):
    """从当前会话 wire.jsonl 尾部重建 (思考强度, swarm是否激活)。"""
    effort, swarm = '', False
    if not session_id:
        return effort, swarm
    hits = glob.glob(os.path.join(SESSIONS, '*', session_id, 'agents', 'main', 'wire.jsonl'))
    if not hits:
        return effort, swarm
    try:
        with open(hits[0], 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - TAIL_BYTES))
            tail = f.read().splitlines()
    except OSError:
        return effort, swarm
    for line in tail:
        if b'thinkingEffort' in line:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            e = r.get('thinkingEffort')
            if not e and isinstance(r.get('event'), dict):
                e = r['event'].get('thinkingEffort')
            if e:
                effort = e
        elif b'swarm_mode' in line:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            t = r.get('type', '')
            if t == 'swarm_mode.enter':
                swarm = True
            elif t == 'swarm_mode.exit':
                swarm = False
    return effort, swarm


def pick(d, *keys, default=''):
    for k in keys:
        v = d.get(k)
        if v not in (None, ''):
            return v
    return default


def main():
    raw = sys.stdin.read()
    snap = {}
    try:
        snap = json.loads(raw) if raw.strip() else {}
    except ValueError:
        pass
    try:
        with open(DEBUG_STDIN, 'w') as f:
            f.write(raw[:4096])
    except OSError:
        pass

    tokens = load_tokens()
    line1 = []

    # 权限模式最前(大写)
    mode = pick(snap, 'permissionMode', 'permission_mode')
    if mode:
        mc = DIM if mode == 'manual' else (YELLOW if mode == 'yolo' else RED)
        parts_mode = c(str(mode).upper(), mc, BOLD if mode != 'manual' else DIM)
        line1.append(parts_mode)

    # 模型(青)·强度(暗) [上下文规格]
    model = pick(snap, 'model', 'model_alias', 'modelAlias')
    if isinstance(model, dict):
        model = pick(model, 'alias', 'id', 'name')
    effort, swarm = session_state(pick(snap, 'sessionId', 'session_id'))
    if model:
        seg = c(str(model).split('/')[-1], CYAN, BOLD) + (c('·' + effort, DIM) if effort else '')
        max_ctx = pick(snap, 'maxContextTokens', 'max_context_tokens', default=0) or 0
        if max_ctx:
            seg += ' ' + c(f'[{fmt_ctx(max_ctx)}]', DIM)
        line1.append(seg)

    # swarm 动效:旋转体 + 反色高亮(激活才显示),整行彩虹循环色边框
    frame = int(time.time())
    if swarm:
        spin = SPINNER[frame % len(SPINNER)]
        line1.append(c256(f'{spin} swarm ', RAINBOW[frame % len(RAINBOW)], BOLD, REVERSE))

    # 上下文条:原生 UI(line 2)已有,这里不重复

    # 5h / 7d 额度条:官方数据 10 分钟内优先,否则回退校准值;带重置倒计时
    if tokens:
        off = tokens.get('official') or {}
        off_fresh = off and (time.time() - off.get('ts', 0)) < OFFICIAL_FRESH_S
        for label, used_key, limit, okey in (('5h', 'h5', PLAN_5H_LIMIT, 'h5'),
                                             ('7d', 'd7', PLAN_7D_LIMIT, 'wk')):
            if off_fresh and off.get(f'{okey}_limit'):
                ratio = min(1.0, off[f'{okey}_used'] / off[f'{okey}_limit'])
                reset_iso = off.get(f'{okey}_reset', '')
            else:
                ratio = min(1.0, tokens.get(used_key, 0) / limit) if limit > 0 else 0
                reset_iso = ''
            filled = min(6, max(0, round(ratio * 6)))
            color = GREEN if ratio < 0.6 else (YELLOW if ratio < 0.85 else RED)
            bar = c('█' * filled, color) + c('░' * (6 - filled), DIM)
            seg = c(f'{label} ', DIM) + bar + ' ' + c(f'{round(100 * ratio)}%', color, BOLD)
            hint = reset_hint(reset_iso)
            if hint:
                seg += c(f' {hint}', DIM)
            line1.append(seg)

    if snap.get('planMode') or snap.get('plan_mode'):
        line1.append(c('plan', BLUE, BOLD))

    git = pick(snap, 'gitBranch', 'git_branch', 'branch')
    if isinstance(git, dict):
        git = pick(git, 'branch', 'name')
    if git:
        line1.append(c(f'⎇ {git}', GREEN))

    # 今日 token + 金额(按官方定价) + 项目目录
    if tokens:
        seg = c(f"今日 {fmt_tokens(tokens.get('today', 0))}", YELLOW)
        cost = tokens.get('today_cost')
        if cost is not None:
            seg += ' ' + c(f'¥{cost:.2f}', YELLOW, BOLD)
        line1.append(seg)
    cwd = pick(snap, 'cwd', 'work_dir', 'workDir')
    if cwd:
        line1.append(c(os.path.basename(str(cwd).rstrip('/')), BLUE))

    out = sep().join(line1) if line1 else 'kimi-code'
    if swarm:
        rc = RAINBOW[frame % len(RAINBOW)]
        out = c256('⟦ ', rc, BOLD) + out + c256(' ⟧', rc, BOLD)  # swarm 彩虹边框逐秒变色
    print(out)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--refresh':
        refresh_cache()
    else:
        main()
