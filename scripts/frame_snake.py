#!/usr/bin/env python3
"""
Wraps a Platane/snk contribution-snake SVG in a panel that matches the other
profile panels, and drops snk's summary bar underneath the grid.

    python3 scripts/frame_snake.py raw/snake-dark.svg dist/snake-dark.svg dark

snk's file is a bare <svg viewBox="-16 -32 880 192"> with a <style> block and
one <rect> per cell. We keep the style and the rects, remove the "u" (summary
bar) rects, and place the grid inside a 900px-wide framed panel with a title.
"""
from __future__ import annotations

import re
import sys

MONO = "'JetBrains Mono','Fira Code','SF Mono',SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"
PALETTES = {
    "dark": dict(bg="#0B0E14", line="#1E2837", muted="#8B98A8", dim="#4B5766", accent="#E3B341"),
    "light": dict(bg="#FFFFFF", line="#D0D7DE", muted="#57606A", dim="#8C959F", accent="#9A6700"),
}


def frame(src: str, theme: str) -> str:
    p = PALETTES[theme]
    m = re.search(r"<svg[^>]*viewBox=\"([^\"]+)\"[^>]*>(.*)</svg>\s*$", src, re.S)
    if not m:
        raise SystemExit("input does not look like an snk svg")
    vx, vy, vw, vh = (float(v) for v in m.group(1).split())
    body = m.group(2)
    body = re.sub(r'<rect class="u[^"]*"[^>]*/>', "", body)      # summary bar
    body = re.sub(r"<desc>.*?</desc>", "", body, flags=re.S)
    # grid extent: cells are 12px on a 16px pitch; find the last row and column
    ys = [float(v) for v in re.findall(r'<rect class="c[^"]*"[^>]*\sy="([\d.]+)"', body)]
    xs = [float(v) for v in re.findall(r'<rect class="c[^"]*"[^>]*\sx="([\d.]+)"', body)]
    grid_w = (max(xs) + 12) if xs else 848
    grid_h = (max(ys) + 12) if ys else 108
    W = 900
    top = 52
    H = int(top + grid_h + 22)
    ox = (W - grid_w) / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Contribution graph with a snake eating a year of commits">\n'
        f'  <rect width="{W}" height="{H}" rx="10" fill="{p["bg"]}"/>\n'
        f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{p["line"]}"/>\n'
        f'  <text x="18" y="27" font-family="{MONO}" font-size="11" font-weight="700" fill="{p["muted"]}" letter-spacing="1.5" xml:space="preserve">CONTRIBUTION TAPE · 52W</text>\n'
        f'  <text x="{W - 18}" y="27" text-anchor="end" font-family="{MONO}" font-size="11" fill="{p["dim"]}" xml:space="preserve">the snake eats a year of commits</text>\n'
        f'  <line x1="0" y1="40.5" x2="{W}" y2="40.5" stroke="{p["line"]}"/>\n'
        f'  <g transform="translate({ox:.1f} {top})">{body}</g>\n'
        f"</svg>\n"
    )


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    src_path, dst_path, theme = sys.argv[1:]
    with open(src_path, encoding="utf-8") as fh:
        src = fh.read()
    out = frame(src, theme)
    with open(dst_path, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"wrote {dst_path} ({len(out) // 1024} KB)")


if __name__ == "__main__":
    main()
