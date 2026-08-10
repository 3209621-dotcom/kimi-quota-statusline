#!/usr/bin/env python3
"""生成 README 演示素材:assets/statusline.png(静态) + assets/swarm.gif(swarm 水波动效)。

素材由项目自身的 statusline.py 真实渲染生成(动效逐帧调 brand_flow),非手工拼贴。
依赖 Pillow;需要本机缓存有官方额度数据(先随便跑一次状态栏即可)。
用法: python3 assets/make_demo.py
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.pop('KIMI_SL_NOCOLOR', None)  # 必须彩色输出
import statusline

ROOT = os.path.join(os.path.dirname(__file__), '..')
OUT_PNG = os.path.join(ROOT, 'assets', 'statusline.png')
OUT_GIF = os.path.join(ROOT, 'assets', 'swarm.gif')

FONT_PATH = '/System/Library/Fonts/Menlo.ttc'
FONT_FALLBACK = '/System/Library/Fonts/Apple Symbols.ttf'  # 覆盖 Menlo 缺的字形(如 ⎇ U+2387)
FONT_SIZE = 15
PAD_X, PAD_Y = 16, 12
SCALE = 2                    # 超采样抗锯齿
BG = (13, 17, 23)            # GitHub 暗色 #0D1117
FG = (224, 224, 224)         # 主题 text token
FPS = 5                      # GIF 帧率;TUI 实际 1fps,这里按动效设计节奏展示
HOLD_LAST = 12               # 结尾静态帧额外停留帧数

# Kimi Code 主题 token 对齐的标准色(深色板)
STD = {
    31: (0xE8, 0x54, 0x54),  # error
    32: (0x4E, 0xC8, 0x7E),  # success
    33: (0xE8, 0xA8, 0x38),  # warning
    34: (0x4F, 0xA8, 0xFF),  # primary
    35: (0xC5, 0x86, 0xC0),
    36: (0x5B, 0xC0, 0xBE),  # accent
    90: (0x6B, 0x6B, 0x6B),  # textMuted
}


def parse_ansi(text):
    """把脚本用到的 ANSI 子集解析成 [(字符, (r,g,b))] 序列。
    支持:38;2;r;g;b 真彩、30-37/90 标准色、1 粗体(提亮)、2 暗化、0 复位。"""
    spans = []
    color, i, n = FG, 0, len(text)
    while i < n:
        if text[i] == '\033' and i + 1 < n and text[i + 1] == '[':
            j = text.index('m', i)
            codes = text[i + 2:j].split(';')
            k = 0
            while k < len(codes):
                v = int(codes[k]) if codes[k] else 0
                if v == 0:
                    color = FG
                elif v == 38 and k + 4 < len(codes) and codes[k + 1] == '2':
                    color = (int(codes[k + 2]), int(codes[k + 3]), int(codes[k + 4]))
                    k += 4
                elif v == 2:
                    color = tuple(int(ch * 0.62) for ch in color)
                elif v == 1:
                    color = tuple(min(255, int(ch * 1.18)) for ch in color)
                elif v in STD:
                    color = STD[v]
                k += 1
            i = j + 1
        else:
            spans.append((text[i], color))
            i += 1
    return spans


def _covered_chars(path):
    """主字体 cmap;无 fontTools 时退化为内置缺失表。"""
    try:
        from fontTools.ttLib import TTCollection, TTFont
        f = TTCollection(path).fonts[0] if path.endswith('.ttc') else TTFont(path, fontNumber=0)
        return set(f.getBestCmap())
    except Exception:
        return None


def render_image(ansi_text):
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE * SCALE)
    fb = ImageFont.truetype(FONT_FALLBACK, FONT_SIZE * SCALE)
    covered = _covered_chars(FONT_PATH)

    def pick_font(ch):
        if covered is not None:
            return font if ord(ch) in covered else fb
        return fb if ch in {'⎇'} else font

    spans = parse_ansi(ansi_text.rstrip('\n'))
    probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    w = int(sum(pick_font(ch).getlength(ch) for ch, _ in spans)) + PAD_X * 2 * SCALE
    h = FONT_SIZE * SCALE + PAD_Y * 2 * SCALE
    img = Image.new('RGB', (w, h), BG)
    d = ImageDraw.Draw(img)
    x = PAD_X * SCALE
    for ch, color in spans:
        fnt = pick_font(ch)
        d.text((x, PAD_Y * SCALE), ch, font=fnt, fill=color)
        x += fnt.getlength(ch)
    return img.resize((w // SCALE, h // SCALE), Image.LANCZOS)


def latest_session_id():
    files = []
    base = os.path.join(statusline.SESSIONS, '*', '*', 'agents', 'main', 'wire.jsonl')
    import glob
    for p in glob.glob(base):
        files.append((os.stat(p).st_mtime, p))
    if not files:
        return ''
    p = max(files)[1]
    return p.split('/')[-4]


def render_line(sid):
    """用真实快照跑一遍脚本,取 stdout 第一行(ANSI)。"""
    snap = {'model': 'K3', 'cwd': os.path.abspath(ROOT),
            'gitBranch': 'main', 'permissionMode': 'yolo', 'planMode': False,
            'maxContextTokens': 1048576, 'sessionId': sid, 'version': '0.34.0'}
    import json
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'statusline.py')],
                       input=json.dumps(snap), capture_output=True, text=True, check=True)
    return r.stdout.rstrip('\n')


def main():
    sid = latest_session_id()
    # 先刷新缓存,保证会话 token 段与官方额度条都在
    subprocess.run([sys.executable, os.path.join(ROOT, 'statusline.py'), '--refresh', sid, 'demo'],
                   check=True)
    line = render_line(sid)
    plain = statusline.ANSI_RE.sub('', line)

    render_image(line).save(OUT_PNG)
    print('written:', OUT_PNG)

    frames = []
    for i in range(int(8 * FPS) + 1):
        frames.append(render_image(statusline.brand_flow(plain, i / FPS)))
    frames.extend([frames[-1]] * HOLD_LAST)
    frames[0].save(OUT_GIF, save_all=True, append_images=frames[1:],
                   duration=int(1000 / FPS), loop=0)
    print('written:', OUT_GIF)


if __name__ == '__main__':
    main()
