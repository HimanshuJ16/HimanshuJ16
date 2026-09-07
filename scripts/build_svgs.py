#!/usr/bin/env python3
"""
Builds every hand-made animated SVG for the profile README.

    python3 scripts/build_svgs.py          # writes assets/*-dark.svg and assets/*-light.svg

Everything is pure SMIL (<animate>, <animateTransform>, <animateMotion>) so it
animates when GitHub embeds the file through <img>/<picture>. No scripts, no
external fonts, no external resources. The dark and light variants are the same
drawing with a different palette, so they stay pixel-identical in layout.
"""
from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

MONO = "'JetBrains Mono','Fira Code','SF Mono',SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"


# --------------------------------------------------------------------------- palette
@dataclass(frozen=True)
class Palette:
    name: str
    bg: str        # canvas
    panel: str     # panel fill
    line: str      # borders / grid
    text: str      # primary text
    muted: str     # secondary text
    dim: str       # very quiet text
    up: str        # bids / positive
    down: str      # asks / negative
    accent: str    # amber highlight
    data: str      # cyan data / packets
    glow: str      # glow colour behind nodes


DARK = Palette(
    name="dark",
    bg="#0B0E14", panel="#111722", line="#1E2837",
    text="#E6EDF3", muted="#8B98A8", dim="#4B5766",
    up="#3FB950", down="#F85149", accent="#E3B341", data="#39C5F2", glow="#39C5F2",
)
LIGHT = Palette(
    name="light",
    bg="#FFFFFF", panel="#F6F8FA", line="#D0D7DE",
    text="#1F2328", muted="#57606A", dim="#8C959F",
    up="#1A7F37", down="#CF222E", accent="#9A6700", data="#0969DA", glow="#0969DA",
)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


# --------------------------------------------------------------------------- helpers
def typed_line(text: str, x: float, y: float, size: float, fill: str, begin: float,
               dur: float, char_w: float | None = None, weight: str = "500",
               cursor_fill: str | None = None, cursor_h: float | None = None,
               keep_cursor: bool = False, clip_id: str = "") -> tuple[str, float]:
    """A <text> revealed character-by-character with a discrete clipPath animation.

    Returns (svg, end_time). The text is given a fixed textLength so the reveal
    steps land exactly on glyph boundaries regardless of the viewer's font.
    """
    n = len(text)
    cw = char_w if char_w else size * 0.6
    total = n * cw
    steps = [round(i * cw, 2) for i in range(n + 1)]
    values = ";".join(fmt(s) for s in steps)
    key_times = ";".join(fmt(i / n) for i in range(n + 1))
    ch = cursor_h if cursor_h else size * 1.15
    cy = y - size * 0.92
    svg = f"""
  <clipPath id="{clip_id}"><rect x="{fmt(x)}" y="{fmt(y - size)}" width="0" height="{fmt(size * 1.5)}">
    <animate attributeName="width" values="{values}" keyTimes="{key_times}" calcMode="discrete" begin="{fmt(begin)}s" dur="{fmt(dur)}s" fill="freeze"/>
  </rect></clipPath>
  <text x="{fmt(x)}" y="{fmt(y)}" font-family="{MONO}" font-size="{fmt(size)}" font-weight="{weight}" fill="{fill}" textLength="{fmt(total)}" lengthAdjust="spacing" clip-path="url(#{clip_id})" xml:space="preserve">{esc(text)}</text>"""
    if cursor_fill:
        # cursor that walks along with the reveal, visible only during this line's window
        cx_values = ";".join(fmt(x + s) for s in steps)
        end = begin + dur
        if keep_cursor:
            svg += f"""
  <rect x="{fmt(x)}" y="{fmt(cy)}" width="{fmt(cw)}" height="{fmt(ch)}" fill="{cursor_fill}" opacity="0">
    <animate attributeName="x" values="{cx_values}" keyTimes="{key_times}" calcMode="discrete" begin="{fmt(begin)}s" dur="{fmt(dur)}s" fill="freeze"/>
    <set attributeName="opacity" to="1" begin="{fmt(begin)}s"/>
    <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" begin="{fmt(end)}s" repeatCount="indefinite"/>
  </rect>"""
        else:
            svg += f"""
  <rect x="{fmt(x)}" y="{fmt(cy)}" width="{fmt(cw)}" height="{fmt(ch)}" fill="{cursor_fill}" opacity="0">
    <animate attributeName="x" values="{cx_values}" keyTimes="{key_times}" calcMode="discrete" begin="{fmt(begin)}s" dur="{fmt(dur)}s" fill="freeze"/>
    <set attributeName="opacity" to="1" begin="{fmt(begin)}s" end="{fmt(end)}s"/>
  </rect>"""
    return svg, begin + dur


def tape(items: list[tuple[str, str]], y: float, size: float, p: Palette, speed: float,
         width: float, sep: str = "  ·  ", pad_item: float = 0.0) -> str:
    """Seamlessly looping ticker tape. items = [(text, colour), ...]. Uses fixed
    textLength per item so the loop length is deterministic in any font."""
    cw = size * 0.6
    parts = []
    x = 0.0
    for text, colour in items:
        w = len(text) * cw
        parts.append((x, text, colour, w))
        x += w
        sw = len(sep) * cw
        parts.append((x, sep, p.dim, sw))
        x += sw + pad_item
    loop_w = x

    def render(offset: float) -> str:
        out = []
        for px, text, colour, w in parts:
            out.append(
                f'<text x="{fmt(px + offset)}" y="{fmt(y)}" font-family="{MONO}" font-size="{fmt(size)}" '
                f'font-weight="500" fill="{colour}" textLength="{fmt(w)}" lengthAdjust="spacing" '
                f'xml:space="preserve">{esc(text)}</text>'
            )
        return "\n      ".join(out)

    dur = loop_w / speed
    return f"""
    <g>
      <animateTransform attributeName="transform" type="translate" from="0 0" to="{fmt(-loop_w)} 0" dur="{fmt(dur)}s" repeatCount="indefinite"/>
      {render(0)}
      {render(loop_w)}
    </g>"""


def svg_open(w: int, h: int, p: Palette, title: str, desc: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">\n'
        f'  <title id="t">{esc(title)}</title>\n  <desc id="d">{esc(desc)}</desc>\n'
    )


# --------------------------------------------------------------------------- 1. header
def build_header(p: Palette) -> str:
    W, H = 900, 380
    s = svg_open(W, H, p, "Himanshu Jangir — full-stack engineer & quant builder",
                 "An animated trading-terminal style profile header: scrolling tape, a typed session, "
                 "a self-drawing candlestick chart and open positions: HeatCodes, Algo-Trading-Skills and the live equity algo bot.")
    s += f"""
  <defs>
    <linearGradient id="fade" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0" stop-color="{p.bg}" stop-opacity="1"/>
      <stop offset="0.06" stop-color="{p.bg}" stop-opacity="0"/>
      <stop offset="0.94" stop-color="{p.bg}" stop-opacity="0"/>
      <stop offset="1" stop-color="{p.bg}" stop-opacity="1"/>
    </linearGradient>
    <linearGradient id="area" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="{p.up}" stop-opacity="0.28"/>
      <stop offset="1" stop-color="{p.up}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="tapeclip"><rect x="0" y="0" width="{W}" height="30"/></clipPath>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2.5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="{W}" height="{H}" rx="10" fill="{p.bg}"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{p.line}"/>
"""
    # ---- tape (top strip)
    items = [
        ("NSE EQUITIES", p.text), ("INTRADAY ▲", p.up), ("NEXT.JS", p.text), ("REACT", p.text), ("TYPESCRIPT", p.text),
        ("PYTHON", p.text), ("FASTAPI", p.text), ("NODE.JS", p.text), ("POSTGRESQL", p.text), ("MONGODB", p.text),
        ("AWS", p.text), ("GCP", p.text), ("DOCKER", p.text), ("REACT NATIVE", p.text),
        ("HEATCODES  IN · UK", p.accent), ("HJ16 ▲ SHIPPING", p.up),
    ]
    s += f'  <g clip-path="url(#tapeclip)">'
    s += tape(items, 19, 11.5, p, speed=42, width=W, sep="   │   ")
    s += f"""
  </g>
  <rect x="0" y="0" width="{W}" height="30" fill="url(#fade)"/>
  <line x1="0" y1="30.5" x2="{W}" y2="30.5" stroke="{p.line}"/>
"""
    # ---- window chrome dots + title
    s += f"""
  <circle cx="18" cy="47" r="4" fill="{p.down}"/><circle cx="32" cy="47" r="4" fill="{p.accent}"/><circle cx="46" cy="47" r="4" fill="{p.up}"/>
  <text x="62" y="51" font-family="{MONO}" font-size="11" fill="{p.dim}" xml:space="preserve">himanshu@desk — session — ~/</text>
  <text x="{W - 16}" y="51" text-anchor="end" font-family="{MONO}" font-size="11" fill="{p.dim}" xml:space="preserve">IST · UTC+05:30</text>
  <line x1="0" y1="62.5" x2="{W}" y2="62.5" stroke="{p.line}"/>
"""
    # ---- typed session (left)
    x0 = 22
    t = 0.35
    seq = [
        ("$ whoami", 13, p.muted, 0.55, "400", False),
        ("Himanshu Jangir", 30, p.text, 1.05, "700", False),
        ("full-stack engineer · co-founder @ HeatCodes", 13, p.muted, 1.25, "500", False),
        ("B.Tech CS @ DSEU · class of 2027 · New Delhi", 13, p.muted, 1.15, "500", False),
        ("$ cat ~/now", 13, p.muted, 0.6, "400", False),
        ("running live-stocks-equity-algo-bot in prod", 13, p.data, 1.0, "500", False),
        ("python · intraday equities · 500+ skills OSS", 13, p.data, 1.0, "500", False),
        ("$ ", 13, p.muted, 0.2, "400", True),
    ]
    y = 96
    gaps = [30, 38, 22, 34, 22, 22, 34, 0]
    clip_defs = ""
    body = ""
    for i, (text, size, fill, dur, weight, last) in enumerate(seq):
        t += 0.12
        part, t = typed_line(text, x0, y, size, fill, t, dur, weight=weight,
                             cursor_fill=p.accent, keep_cursor=last, clip_id=f"tl{i}")
        body += part
        y += gaps[i]
    s += body
    # ---- divider between left and right
    s += f'\n  <line x1="548.5" y1="63" x2="548.5" y2="{H - 30}" stroke="{p.line}"/>'

    # ---- chart (right)
    cx0, cy0, cw, chh = 566, 82, 318, 150
    rnd = random.Random(1618)
    n = 30
    bw, gap = 7.6, 3.0
    price = 100.0
    candles = []
    for i in range(n):
        drift = 0.55
        o = price
        c = o + drift + rnd.uniform(-3.2, 3.2)
        hi = max(o, c) + rnd.uniform(0.2, 2.0)
        lo = min(o, c) - rnd.uniform(0.2, 2.0)
        candles.append((o, hi, lo, c))
        price = c
    lo_all = min(c[2] for c in candles)
    hi_all = max(c[1] for c in candles)
    pad = (hi_all - lo_all) * 0.12

    def sy(v: float) -> float:
        return cy0 + chh - (v - (lo_all - pad)) / ((hi_all + pad) - (lo_all - pad)) * chh

    s += f"""
  <text x="{cx0}" y="{cy0 - 6}" font-family="{MONO}" font-size="11" font-weight="700" fill="{p.text}" xml:space="preserve">HJ16</text>
  <text x="{cx0 + 38}" y="{cy0 - 6}" font-family="{MONO}" font-size="11" fill="{p.dim}" xml:space="preserve">· 1D · shipping since 2022</text>
  <text x="{cx0 + cw}" y="{cy0 - 6}" text-anchor="end" font-family="{MONO}" font-size="11" font-weight="600" fill="{p.up}" xml:space="preserve">▲ LONG</text>
"""
    # grid
    for k in range(5):
        gy = cy0 + k * chh / 4
        s += f'  <line x1="{cx0}" y1="{fmt(gy)}" x2="{cx0 + cw}" y2="{fmt(gy)}" stroke="{p.line}" stroke-dasharray="2 4"/>\n'
    # area under closes + candles, revealed by a growing clip
    pts = []
    for i, (o, hi, lo, c) in enumerate(candles):
        x = cx0 + i * (bw + gap) + bw / 2
        pts.append((x, sy(c)))
    area = f"M{fmt(pts[0][0])},{fmt(cy0 + chh)} " + " ".join(f"L{fmt(x)},{fmt(yv)}" for x, yv in pts) + f" L{fmt(pts[-1][0])},{fmt(cy0 + chh)} Z"
    line = "M" + " L".join(f"{fmt(x)},{fmt(yv)}" for x, yv in pts)
    s += f"""
  <clipPath id="reveal"><rect x="{cx0}" y="{cy0 - 10}" width="0" height="{chh + 20}">
    <animate attributeName="width" from="0" to="{cw}" begin="0.4s" dur="3.4s" calcMode="spline" keySplines="0.2 0 0.2 1" fill="freeze"/>
  </rect></clipPath>
  <g clip-path="url(#reveal)">
    <path d="{area}" fill="url(#area)"/>
    <path d="{line}" fill="none" stroke="{p.up}" stroke-opacity="0.55" stroke-width="1"/>
"""
    for i, (o, hi, lo, c) in enumerate(candles):
        x = cx0 + i * (bw + gap)
        col = p.up if c >= o else p.down
        top, bot = sy(max(o, c)), sy(min(o, c))
        h = max(1.2, bot - top)
        s += (f'    <line x1="{fmt(x + bw / 2)}" y1="{fmt(sy(hi))}" x2="{fmt(x + bw / 2)}" y2="{fmt(sy(lo))}" stroke="{col}" stroke-width="1"/>\n'
              f'    <rect x="{fmt(x)}" y="{fmt(top)}" width="{fmt(bw)}" height="{fmt(h)}" fill="{col}" rx="1"/>\n')
    s += "  </g>\n"
    # last price line + label, pulsing dot at last close
    lx, ly = pts[-1]
    s += f"""
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="3.6s" dur="0.6s" fill="freeze"/>
    <line x1="{cx0}" y1="{fmt(ly)}" x2="{cx0 + cw}" y2="{fmt(ly)}" stroke="{p.accent}" stroke-width="1" stroke-dasharray="3 3"/>
    <rect x="{cx0 + cw - 58}" y="{fmt(ly - 9)}" width="58" height="18" rx="3" fill="{p.accent}"/>
    <text x="{cx0 + cw - 29}" y="{fmt(ly + 4)}" text-anchor="middle" font-family="{MONO}" font-size="10.5" font-weight="700" fill="{p.bg}" xml:space="preserve">LAST ▲</text>
    <circle cx="{fmt(lx)}" cy="{fmt(ly)}" r="3" fill="{p.accent}" filter="url(#glow)">
      <animate attributeName="r" values="3;6;3" dur="2.4s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="1;0.35;1" dur="2.4s" repeatCount="indefinite"/>
    </circle>
  </g>
"""
    # ---- open positions (right, bottom)
    py = cy0 + chh + 30
    s += f"""
  <line x1="549" y1="{py - 18}" x2="{W}" y2="{py - 18}" stroke="{p.line}"/>
  <text x="{cx0}" y="{py}" font-family="{MONO}" font-size="10.5" font-weight="700" fill="{p.muted}" letter-spacing="1.5" xml:space="preserve">OPEN POSITIONS</text>
  <text x="{cx0 + cw}" y="{py}" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{p.dim}" xml:space="preserve">SIDE · SYMBOL · STATUS</text>
"""
    positions = [
        ("LONG", "heatcodes", "clients in IN · UK", p.up, p.muted),
        ("LONG", "algo-trading-skills", "500+ skills · OSS", p.up, p.muted),
        ("LONG", "live-stocks-equity-algo-bot", "PROD READY", p.up, p.up),
    ]
    for i, (side, sym, status, col, scol) in enumerate(positions):
        ry = py + 16 + i * 24
        b = 4.0 + i * 0.35
        s += f"""
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="{fmt(b)}s" dur="0.5s" fill="freeze"/>
    <rect x="{cx0}" y="{ry - 11}" width="38" height="16" rx="3" fill="{col}" fill-opacity="0.16"/>
    <text x="{cx0 + 19}" y="{ry + 1}" text-anchor="middle" font-family="{MONO}" font-size="9.5" font-weight="700" fill="{col}" xml:space="preserve">{side}</text>
    <text x="{cx0 + 48}" y="{ry + 1}" font-family="{MONO}" font-size="12" font-weight="600" fill="{p.text}" xml:space="preserve">{esc(sym)}</text>
    <text x="{cx0 + cw}" y="{ry + 1}" text-anchor="end" font-family="{MONO}" font-size="10.5" font-weight="{'700' if scol != p.muted else '400'}" fill="{scol}" xml:space="preserve">{esc(status)}</text>
  </g>"""
    # ---- status bar (contact) across the bottom
    by = H - 30
    s += f"""
  <path d="M0,{by} H{W} V{H - 10} a10,10 0 0 1 -10,10 H10 a10,10 0 0 1 -10,-10 Z" fill="{p.panel}"/>
  <line x1="0" y1="{by + 0.5}" x2="{W}" y2="{by + 0.5}" stroke="{p.line}"/>
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="5.6s" dur="0.8s" fill="freeze"/>
    <circle cx="24" cy="{by + 15}" r="3.5" fill="{p.up}">
      <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>
    </circle>
    <text x="34" y="{by + 19}" font-family="{MONO}" font-size="11" font-weight="600" fill="{p.up}" xml:space="preserve">OPEN TO WORK</text>
    <text x="150" y="{by + 19}" font-family="{MONO}" font-size="11" fill="{p.muted}" xml:space="preserve">web  himanshujangir.com</text>
    <text x="370" y="{by + 19}" font-family="{MONO}" font-size="11" fill="{p.muted}" xml:space="preserve">mail  himanshujangir16@gmail.com</text>
    <text x="{W - 16}" y="{by + 19}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{p.muted}" xml:space="preserve">in/himanshujangir16</text>
  </g>"""
    s += "\n</svg>\n"
    return s


# --------------------------------------------------------------------------- 2. order book (stack)
def build_orderbook(p: Palette) -> str:
    W, H = 900, 286
    s = svg_open(W, H, p, "Order book: the stack",
                 "The tech stack drawn as a live order book: frontend on the bid side, backend on the ask side, "
                 "infrastructure in the spread. Depth bars breathe continuously.")
    s += f"""
  <rect width="{W}" height="{H}" rx="10" fill="{p.bg}"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{p.line}"/>
  <text x="18" y="27" font-family="{MONO}" font-size="11" font-weight="700" fill="{p.muted}" letter-spacing="1.5" xml:space="preserve">ORDER BOOK · HJ16 · DEPTH</text>
  <text x="{W - 18}" y="27" text-anchor="end" font-family="{MONO}" font-size="11" fill="{p.dim}" xml:space="preserve">what I build with, and how deep</text>
  <line x1="0" y1="40.5" x2="{W}" y2="40.5" stroke="{p.line}"/>
"""
    bids = [  # (name, note, depth 0..1)
        ("Next.js", "App Router · RSC · edge", 1.00),
        ("React", "hooks · suspense · state", 0.92),
        ("TypeScript", "strict · zod · tRPC", 0.90),
        ("React Native", "Expo · iOS + Android", 0.62),
        ("Tailwind", "design systems", 0.70),
    ]
    asks = [
        ("Python · FastAPI", "async · pydantic · workers", 1.00),
        ("Node.js", "REST · websockets · queues", 0.86),
        ("PostgreSQL", "schema design · indexes", 0.88),
        ("MongoDB", "aggregation · sharding", 0.66),
        ("pandas · NumPy", "backtests · signals · risk", 0.78),
    ]
    row_h = 30
    top = 68
    mid = W / 2
    half = 350   # bar area width per side
    # column headers
    s += f"""
  <text x="22" y="58" font-family="{MONO}" font-size="10" font-weight="700" fill="{p.up}" letter-spacing="1.2" xml:space="preserve">BID · FRONTEND</text>
  <text x="{fmt(mid - 20)}" y="58" text-anchor="end" font-family="{MONO}" font-size="10" fill="{p.dim}" xml:space="preserve">depth</text>
  <text x="{fmt(mid + 20)}" y="58" font-family="{MONO}" font-size="10" fill="{p.dim}" xml:space="preserve">depth</text>
  <text x="{W - 22}" y="58" text-anchor="end" font-family="{MONO}" font-size="10" font-weight="700" fill="{p.down}" letter-spacing="1.2" xml:space="preserve">BACKEND · ASK</text>
"""
    for i in range(5):
        y = top + i * row_h
        bn, bnote, bd = bids[i]
        an, anote, ad = asks[i]
        # bid bar grows from centre toward the left
        bw = half * bd
        aw = half * ad
        d = 5.2 + i * 0.6
        # breathing values around the base depth
        bvals = ";".join(fmt(v) for v in (bw, bw * 0.86, bw, bw * 0.93, bw))
        bxs = ";".join(fmt(mid - 8 - v) for v in (bw, bw * 0.86, bw, bw * 0.93, bw))
        avals = ";".join(fmt(v) for v in (aw, aw * 0.9, aw, aw * 0.84, aw))
        s += f"""
  <g>
    <rect x="{fmt(mid - 8 - bw)}" y="{y}" width="{fmt(bw)}" height="{row_h - 6}" rx="3" fill="{p.up}" fill-opacity="0.13">
      <animate attributeName="width" values="{bvals}" dur="{fmt(d)}s" repeatCount="indefinite" calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1"/>
      <animate attributeName="x" values="{bxs}" dur="{fmt(d)}s" repeatCount="indefinite" calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1"/>
    </rect>
    <rect x="{fmt(mid - 10)}" y="{y}" width="2" height="{row_h - 6}" fill="{p.up}"/>
    <text x="22" y="{y + 16}" font-family="{MONO}" font-size="13" font-weight="700" fill="{p.text}" xml:space="preserve">{esc(bn)}</text>
    <text x="{fmt(mid - 20)}" y="{y + 16}" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{p.muted}" xml:space="preserve">{esc(bnote)}</text>
    <rect x="{fmt(mid + 8)}" y="{y}" width="{fmt(aw)}" height="{row_h - 6}" rx="3" fill="{p.down}" fill-opacity="0.13">
      <animate attributeName="width" values="{avals}" dur="{fmt(d + 0.8)}s" repeatCount="indefinite" calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1"/>
    </rect>
    <rect x="{fmt(mid + 8)}" y="{y}" width="2" height="{row_h - 6}" fill="{p.down}"/>
    <text x="{fmt(mid + 20)}" y="{y + 16}" font-family="{MONO}" font-size="10.5" fill="{p.muted}" xml:space="preserve">{esc(anote)}</text>
    <text x="{W - 22}" y="{y + 16}" text-anchor="end" font-family="{MONO}" font-size="13" font-weight="700" fill="{p.text}" xml:space="preserve">{esc(an)}</text>
  </g>"""
    # spread row: infra
    sy_ = top + 5 * row_h + 10
    s += f"""
  <line x1="0" y1="{sy_ - 6}" x2="{W}" y2="{sy_ - 6}" stroke="{p.line}"/>
  <text x="22" y="{sy_ + 20}" font-family="{MONO}" font-size="10" font-weight="700" fill="{p.accent}" letter-spacing="1.2" xml:space="preserve">SPREAD · INFRA</text>
"""
    chips = ["AWS", "GCP", "Docker", "GitHub Actions", "Vercel", "Nginx", "Redis", "Linux"]
    cx = 150
    for i, c in enumerate(chips):
        w = len(c) * 7.2 + 20
        s += f"""
  <g>
    <rect x="{fmt(cx)}" y="{sy_ + 6}" width="{fmt(w)}" height="20" rx="10" fill="{p.accent}" fill-opacity="0.12" stroke="{p.accent}" stroke-opacity="0.45">
      <animate attributeName="stroke-opacity" values="0.35;0.9;0.35" dur="4s" begin="{fmt(i * 0.5)}s" repeatCount="indefinite"/>
    </rect>
    <text x="{fmt(cx + w / 2)}" y="{sy_ + 20}" text-anchor="middle" font-family="{MONO}" font-size="11" font-weight="600" fill="{p.text}" xml:space="preserve">{esc(c)}</text>
  </g>"""
        cx += w + 10
    s += "\n</svg>\n"
    return s


# --------------------------------------------------------------------------- 3. pipeline (architecture boots up)
def build_pipeline(p: Palette) -> str:
    W, H = 900, 366
    s = svg_open(W, H, p, "System pipeline booting",
                 "The intraday equity trading platform boots service by service: broker session, news candidates, "
                 "market feed, Neon Postgres and Cloudflare R2, the Socket.IO relay on Render, then the Next.js desk "
                 "and Expo mobile app. Packets then stream end to end and telemetry feeds back into the engine.")
    s += f"""
  <defs>
    <filter id="nglow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0,0 L8,4 L0,8 z" fill="{p.line}"/>
    </marker>
  </defs>
  <rect width="{W}" height="{H}" rx="10" fill="{p.bg}"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{p.line}"/>
  <text x="18" y="27" font-family="{MONO}" font-size="11" font-weight="700" fill="{p.muted}" letter-spacing="1.5" xml:space="preserve">SYSTEM · LIVE-STOCKS-EQUITY-ALGO-BOT · BOOT</text>
  <text x="{W - 18}" y="27" text-anchor="end" font-family="{MONO}" font-size="11" fill="{p.dim}" xml:space="preserve">how the pieces fit</text>
  <line x1="0" y1="40.5" x2="{W}" y2="40.5" stroke="{p.line}"/>
"""
    # nodes: (id, title line 1, title line 2, subtitle, x, colour)
    nw, nh = 138, 74
    ny = 68
    xs = [22, 200, 378, 556, 734]
    nodes = [
        ("feed",  "MARKET & DATA", "FEED",            "news · broker ticks",   xs[0], p.data),
        ("strat", "STRATEGY ENGINE", "(PYTHON VPS)",  "single mutator loop", xs[1], p.accent),
        ("relay", "REALTIME RELAY", "(RENDER NODE.JS)", "Socket.IO · push",    xs[2], p.up),
        ("db",    "PERSISTENCE / R2", "(NEON POSTGRES)", "trades · curves",    xs[3], p.up),
        ("ui",    "TRADING DESK &", "EXPO MOBILE APP", "Next 16 · Expo", xs[4], p.text),
    ]
    # boot log (bottom)
    boot = [
        (0.10, "broker session authenticated (totp auto-login)", None),
        (0.85, "news pre-market candidates scraped (leverage >= 5x)", "strat"),
        (1.40, "mounting market feed & warm-up candle aggregators", "feed"),
        (2.15, "neon postgres connected · cloudflare r2 session bucket primed", "db"),
        (2.90, "socket.io relay handshake verified (render) · expo push ready", "relay"),
        (3.65, "next.js brutalist desk hydrated · expo mobile client connected", "ui"),
        (4.30, "all systems nominal · awaiting 09:21 volume promotion pass", "live"),
    ]
    boot_time = {b[2]: b[0] for b in boot if b[2]}
    ymid = ny + nh / 2
    edges = []
    for i in range(len(nodes) - 1):
        x1 = nodes[i][4] + nw
        x2 = nodes[i + 1][4]
        t = max(boot_time[nodes[i][0]], boot_time[nodes[i + 1][0]])
        edges.append((f"e{i}", f"M{x1},{ymid} L{x2},{ymid}", t))
    # telemetry bus: desk and relay drop down to a bus that feeds back into the engine
    fb_y = ny + nh + 24
    cx_strat = xs[1] + nw / 2
    cx_relay = xs[2] + nw / 2
    cx_ui = xs[4] + nw / 2
    bus = f"M{cx_ui},{ny + nh} L{cx_ui},{fb_y} L{cx_strat},{fb_y} L{cx_strat},{ny + nh}"
    drop = f"M{cx_relay},{ny + nh} L{cx_relay},{fb_y}"
    for eid, d, t in edges:
        s += f"""
  <path id="{eid}" d="{d}" fill="none" stroke="{p.line}" stroke-width="1.5" marker-end="url(#arr)" opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="{fmt(t - 0.2)}s" dur="0.4s" fill="freeze"/>
  </path>
  <path d="{d}" fill="none" stroke="{p.data}" stroke-opacity="0.5" stroke-width="1.5" stroke-dasharray="4 8" opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="4.3s" dur="0.8s" fill="freeze"/>
    <animate attributeName="stroke-dashoffset" from="24" to="0" dur="1.2s" begin="4.3s" repeatCount="indefinite"/>
  </path>"""
    s += f"""
  <path id="efb" d="{bus}" fill="none" stroke="{p.line}" stroke-width="1.2" stroke-dasharray="3 4" marker-end="url(#arr)" opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="3.7s" dur="0.5s" fill="freeze"/>
  </path>
  <path d="{drop}" fill="none" stroke="{p.line}" stroke-width="1.2" stroke-dasharray="3 4" opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="3.7s" dur="0.5s" fill="freeze"/>
  </path>
  <rect x="{fmt((cx_strat + cx_ui) / 2 - 128)}" y="{fb_y - 8}" width="256" height="16" fill="{p.bg}" opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="3.9s" dur="0.4s" fill="freeze"/>
  </rect>
  <text x="{fmt((cx_strat + cx_ui) / 2)}" y="{fb_y + 4}" text-anchor="middle" font-family="{MONO}" font-size="9.5" fill="{p.dim}" opacity="0" xml:space="preserve">fills · trailing stops · p&amp;l · telemetry
    <animate attributeName="opacity" from="0" to="1" begin="3.9s" dur="0.5s" fill="freeze"/>
  </text>"""
    for nid, t1, t2, sub, x, col in nodes:
        t = boot_time[nid]
        s += f"""
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="{fmt(t)}s" dur="0.45s" fill="freeze"/>
    <rect x="{x}" y="{ny}" width="{nw}" height="{nh}" rx="8" fill="{col}" fill-opacity="0.16" filter="url(#nglow)">
      <animate attributeName="fill-opacity" values="0.16;0.32;0.16" dur="3.2s" begin="{fmt(t + 0.4)}s" repeatCount="indefinite"/>
    </rect>
    <rect x="{x}" y="{ny}" width="{nw}" height="{nh}" rx="8" fill="{p.panel}" stroke="{col}" stroke-opacity="0.75"/>
    <circle cx="{x + 14}" cy="{ny + 17}" r="3" fill="{col}">
      <animate attributeName="opacity" values="1;0.25;1" dur="1.6s" begin="{fmt(t + 0.4)}s" repeatCount="indefinite"/>
    </circle>
    <text x="{x + 24}" y="{ny + 21}" font-family="{MONO}" font-size="10.5" font-weight="700" fill="{p.text}" xml:space="preserve">{esc(t1)}</text>
    <text x="{x + 24}" y="{ny + 35}" font-family="{MONO}" font-size="10.5" font-weight="700" fill="{p.text}" xml:space="preserve">{esc(t2)}</text>
    <text x="{x + 12}" y="{ny + 58}" font-family="{MONO}" font-size="9.5" fill="{p.muted}" xml:space="preserve">{esc(sub)}</text>
  </g>"""
    for i, (eid, d, t) in enumerate(edges):
        for k in range(2):
            s += f"""
  <circle r="3" fill="{p.data}" filter="url(#nglow)" opacity="0">
    <set attributeName="opacity" to="1" begin="{fmt(4.6 + k * 0.9 + i * 0.15)}s"/>
    <animateMotion dur="1.8s" begin="{fmt(4.6 + k * 0.9 + i * 0.15)}s" repeatCount="indefinite"><mpath xlink:href="#{eid}"/></animateMotion>
  </circle>"""
    s += f"""
  <circle r="2.5" fill="{p.accent}" opacity="0">
    <set attributeName="opacity" to="1" begin="5.2s"/>
    <animateMotion dur="4s" begin="5.2s" repeatCount="indefinite"><mpath xlink:href="#efb"/></animateMotion>
  </circle>"""
    # runtime rail
    ry = fb_y + 22
    rail = "Ubuntu 24.04 VPS · systemd · Render · Vercel Edge · Neon Serverless · Cloudflare R2 · Expo EAS · Broker API"
    s += f"""
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="0.1s" dur="0.6s" fill="freeze"/>
    <rect x="22" y="{ry}" width="{W - 44}" height="26" rx="6" fill="{p.panel}" stroke="{p.line}"/>
    <text x="36" y="{ry + 17}" font-family="{MONO}" font-size="10" font-weight="700" fill="{p.muted}" letter-spacing="1.2" xml:space="preserve">RUNTIME</text>
    <text x="118" y="{ry + 17}" font-family="{MONO}" font-size="10.5" fill="{p.text}" xml:space="preserve">{esc(rail)}</text>
    <rect x="22" y="{ry}" width="120" height="26" rx="6" fill="{p.data}" fill-opacity="0.12">
      <animate attributeName="x" from="22" to="{W - 22 - 120}" dur="9s" begin="0.5s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1"/>
    </rect>
  </g>"""
    # boot log
    ly = ry + 52
    s += f"""
  <line x1="0" y1="{ly - 16}" x2="{W}" y2="{ly - 16}" stroke="{p.line}"/>
  <text x="22" y="{ly}" font-family="{MONO}" font-size="10" font-weight="700" fill="{p.muted}" letter-spacing="1.2" xml:space="preserve">BOOT LOG</text>"""
    for i, (t, msg, nid) in enumerate(boot):
        yy = ly + 18 + i * 14
        live = nid == "live"
        ok_col = p.accent if live else p.up
        tag = "LIVE " if live else "  OK "
        s += f"""
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="{fmt(t)}s" dur="0.2s" fill="freeze"/>
    <text x="22" y="{yy}" font-family="{MONO}" font-size="10" fill="{p.dim}" xml:space="preserve">[{t:5.2f}s]</text>
    <text x="84" y="{yy}" font-family="{MONO}" font-size="10" fill="{p.text}" xml:space="preserve">{esc(msg)}</text>
    <text x="{W - 22}" y="{yy}" text-anchor="end" font-family="{MONO}" font-size="10" font-weight="700" fill="{ok_col}" xml:space="preserve">[{tag}]</text>
  </g>"""
    s += "\n</svg>\n"
    return s


# --------------------------------------------------------------------------- 4. footer tape
def build_footer(p: Palette) -> str:
    W, H = 900, 34
    s = svg_open(W, H, p, "Session close tape",
                 "A looping ticker tape with links and a sign-off.")
    s += f"""
  <defs>
    <linearGradient id="fade2" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0" stop-color="{p.bg}" stop-opacity="1"/>
      <stop offset="0.07" stop-color="{p.bg}" stop-opacity="0"/>
      <stop offset="0.93" stop-color="{p.bg}" stop-opacity="0"/>
      <stop offset="1" stop-color="{p.bg}" stop-opacity="1"/>
    </linearGradient>
    <clipPath id="fclip"><rect x="0" y="0" width="{W}" height="{H}"/></clipPath>
  </defs>
  <rect width="{W}" height="{H}" rx="8" fill="{p.bg}"/>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="8" fill="none" stroke="{p.line}"/>
  <g clip-path="url(#fclip)">"""
    items = [
        ("SESSION CLOSE", p.accent), ("thanks for reading the tape", p.muted),
        ("himanshujangir.com", p.text), ("github.com/HimanshuJ16", p.text),
        ("linkedin.com/in/himanshujangir16", p.text), ("himanshujangir16@gmail.com", p.text),
        ("HJ16 ▲ open to interesting problems", p.up), ("New Delhi · IST", p.muted),
    ]
    s += tape(items, 21, 11.5, p, speed=38, width=W, sep="   │   ")
    s += f"""
  </g>
  <rect x="0" y="0" width="{W}" height="{H}" rx="8" fill="url(#fade2)"/>
</svg>
"""
    return s


# --------------------------------------------------------------------------- 5. section rule (tiny divider)
def build_rule(label: str, p: Palette, fname: str) -> str:
    W, H = 900, 26
    s = svg_open(W, H, p, label, "Section divider styled as a terminal panel title.")
    n = len(label)
    s += f"""
  <rect width="{W}" height="{H}" fill="{p.bg}"/>
  <line x1="0" y1="{H / 2}" x2="{W}" y2="{H / 2}" stroke="{p.line}"/>
  <rect x="0" y="0" width="{fmt(n * 7.3 + 30)}" height="{H}" fill="{p.bg}"/>
  <text x="0" y="17" font-family="{MONO}" font-size="11" font-weight="700" fill="{p.muted}" letter-spacing="1.8" xml:space="preserve">{esc(label)}</text>
  <rect x="{fmt(n * 7.3 + 8)}" y="{H / 2 - 2}" width="4" height="4" fill="{p.accent}">
    <animate attributeName="opacity" values="1;0.2;1" dur="2.6s" repeatCount="indefinite"/>
  </rect>
</svg>
"""
    return s


# --------------------------------------------------------------------------- main
def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    rules = [
        ("rule-positions", "▌ POSITIONS   what I'm building"),
        ("rule-system", "▌ SYSTEM   how it's wired"),
        ("rule-book", "▌ BOOK   the stack, by depth"),
        ("rule-tape", "▌ TAPE   live activity"),
        ("rule-execute", "▌ EXECUTE   get in touch"),
    ]
    for p in (DARK, LIGHT):
        files = {
            f"header-{p.name}.svg": build_header(p),
            f"orderbook-{p.name}.svg": build_orderbook(p),
            f"pipeline-{p.name}.svg": build_pipeline(p),
            f"footer-{p.name}.svg": build_footer(p),
        }
        for fname, label in rules:
            files[f"{fname}-{p.name}.svg"] = build_rule(label, p, fname)
        for fname, content in files.items():
            path = os.path.join(OUT, fname)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            print(f"wrote {path} ({len(content.encode()) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
