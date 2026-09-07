#!/usr/bin/env python3
"""
Renders the TAPE panel: recent public GitHub activity as an order-fill blotter.

    GITHUB_TOKEN=... python3 scripts/blotter.py --user HimanshuJ16 --out dist

Writes dist/blotter-dark.svg and dist/blotter-light.svg. Standard library only,
so it runs on a bare GitHub Actions runner. Every event type is mapped to a
"fill" row: side (BUY = adds work, SELL = closes/merges, MKT = misc), symbol
(repository), quantity (commits, files, etc.) and a relative timestamp. Rows fade
in one after another; a LIVE dot pulses. If the API is unreachable the script
still writes a valid SVG so the workflow never leaves a broken image behind.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

MONO = "'JetBrains Mono','Fira Code','SF Mono',SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"

PALETTES = {
    "dark": dict(bg="#0B0E14", panel="#111722", line="#1E2837", text="#E6EDF3", muted="#8B98A8",
                 dim="#4B5766", up="#3FB950", down="#F85149", accent="#E3B341", data="#39C5F2"),
    "light": dict(bg="#FFFFFF", panel="#F6F8FA", line="#D0D7DE", text="#1F2328", muted="#57606A",
                  dim="#8C959F", up="#1A7F37", down="#CF222E", accent="#9A6700", data="#0969DA"),
}

W, ROW_H, MAX_ROWS = 900, 26, 8


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def api(url: str, token: str | None):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-blotter",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def rel(ts: str, now: dt.datetime) -> str:
    t = dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    d = now - t
    s = int(d.total_seconds())
    if s < 3600:
        return f"{max(1, s // 60)}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def to_fill(ev: dict, now: dt.datetime):
    """Map one GitHub event to (side, symbol, description, qty, when, colour_key)."""
    kind = ev.get("type")
    repo = ev.get("repo", {}).get("name", "?").split("/")[-1]
    pl = ev.get("payload", {})
    when = rel(ev.get("created_at", now.strftime("%Y-%m-%dT%H:%M:%SZ")), now)
    if kind == "PushEvent":
        n = len(pl.get("commits", [])) or pl.get("size", 0) or 1
        branch = pl.get("ref", "").split("/")[-1]
        msg = (pl.get("commits") or [{}])[-1].get("message", "").splitlines()[0] if pl.get("commits") else ""
        return ("BUY", repo, f"push · {branch} · {msg}"[:58], f"{n} commit{'s' if n != 1 else ''}", when, "up")
    if kind == "PullRequestEvent":
        act = pl.get("action")
        pr = pl.get("pull_request", {})
        merged = pr.get("merged")
        side = "SELL" if (act == "closed" and merged) else ("BUY" if act == "opened" else "MKT")
        label = "merged" if merged else act
        return (side, repo, f"pr #{pr.get('number', '?')} {label} · {pr.get('title', '')}"[:58],
                f"+{pr.get('additions', 0)}/-{pr.get('deletions', 0)}" if pr.get("additions") is not None else "", when,
                "down" if side == "SELL" else "up" if side == "BUY" else "accent")
    if kind == "CreateEvent":
        rt = pl.get("ref_type")
        return ("BUY", repo, f"created {rt} {pl.get('ref') or ''}".strip()[:58], "new", when, "up")
    if kind == "IssuesEvent":
        iss = pl.get("issue", {})
        return ("MKT", repo, f"issue #{iss.get('number', '?')} {pl.get('action')} · {iss.get('title', '')}"[:58], "", when, "accent")
    if kind == "IssueCommentEvent":
        return ("MKT", repo, f"comment on #{pl.get('issue', {}).get('number', '?')}"[:58], "", when, "data")
    if kind == "ReleaseEvent":
        return ("SELL", repo, f"release {pl.get('release', {}).get('tag_name', '')}"[:58], "shipped", when, "down")
    if kind == "WatchEvent":
        return ("MKT", repo, "starred", "", when, "accent")
    if kind == "ForkEvent":
        return ("BUY", repo, "forked", "", when, "up")
    if kind == "PullRequestReviewEvent":
        return ("MKT", repo, f"reviewed pr #{pl.get('pull_request', {}).get('number', '?')}"[:58], "", when, "data")
    return None


def render(theme: str, fills: list, stats: dict, stamp: str) -> str:
    p = PALETTES[theme]
    n = max(len(fills), 1)
    H = 74 + n * ROW_H + 14
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Recent GitHub activity blotter">\n'
         f'  <rect width="{W}" height="{H}" rx="10" fill="{p["bg"]}"/>\n'
         f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{p["line"]}"/>\n'
         f'  <text x="18" y="27" font-family="{MONO}" font-size="11" font-weight="700" fill="{p["muted"]}" letter-spacing="1.5" xml:space="preserve">BLOTTER · FILLS · github.com/HimanshuJ16</text>\n'
         f'  <circle cx="{W - 74}" cy="23" r="3.5" fill="{p["up"]}"><animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/></circle>\n'
         f'  <text x="{W - 64}" y="27" font-family="{MONO}" font-size="11" font-weight="700" fill="{p["up"]}" xml:space="preserve">LIVE</text>\n'
         f'  <line x1="0" y1="40.5" x2="{W}" y2="40.5" stroke="{p["line"]}"/>\n')
    # stats strip
    sx = 18
    for k, v in stats.items():
        s += (f'  <text x="{sx}" y="58" font-family="{MONO}" font-size="10" fill="{p["dim"]}" xml:space="preserve">{esc(k)}</text>\n'
              f'  <text x="{sx + len(k) * 6.2 + 6}" y="58" font-family="{MONO}" font-size="10.5" font-weight="700" fill="{p["text"]}" xml:space="preserve">{esc(str(v))}</text>\n')
        sx += len(k) * 6.2 + len(str(v)) * 6.6 + 34
    s += f'  <text x="{W - 18}" y="58" text-anchor="end" font-family="{MONO}" font-size="10" fill="{p["dim"]}" xml:space="preserve">refreshed {esc(stamp)}</text>\n'
    s += f'  <line x1="0" y1="66.5" x2="{W}" y2="66.5" stroke="{p["line"]}"/>\n'
    # header row
    hy = 82
    s += (f'  <text x="18" y="{hy}" font-family="{MONO}" font-size="9.5" fill="{p["dim"]}" letter-spacing="1" xml:space="preserve">SIDE</text>\n'
          f'  <text x="70" y="{hy}" font-family="{MONO}" font-size="9.5" fill="{p["dim"]}" letter-spacing="1" xml:space="preserve">SYMBOL</text>\n'
          f'  <text x="270" y="{hy}" font-family="{MONO}" font-size="9.5" fill="{p["dim"]}" letter-spacing="1" xml:space="preserve">FILL</text>\n'
          f'  <text x="{W - 90}" y="{hy}" text-anchor="end" font-family="{MONO}" font-size="9.5" fill="{p["dim"]}" letter-spacing="1" xml:space="preserve">QTY</text>\n'
          f'  <text x="{W - 18}" y="{hy}" text-anchor="end" font-family="{MONO}" font-size="9.5" fill="{p["dim"]}" letter-spacing="1" xml:space="preserve">AGE</text>\n')
    if not fills:
        fills = [("MKT", "—", "no public activity fetched · check back after the next refresh", "", "", "accent")]
    for i, (side, sym, desc, qty, when, ck) in enumerate(fills):
        y = hy + 12 + i * ROW_H
        col = p[ck]
        s += (f'  <g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{0.2 + i * 0.18:.2f}s" dur="0.35s" fill="freeze"/>\n'
              f'    <rect x="12" y="{y}" width="{W - 24}" height="{ROW_H - 4}" rx="4" fill="{p["panel"]}" opacity="{"1" if i % 2 == 0 else "0"}"/>\n'
              f'    <rect x="18" y="{y + 4}" width="40" height="{ROW_H - 12}" rx="3" fill="{col}" fill-opacity="0.16"/>\n'
              f'    <text x="38" y="{y + 15}" text-anchor="middle" font-family="{MONO}" font-size="9.5" font-weight="700" fill="{col}" xml:space="preserve">{side}</text>\n'
              f'    <text x="70" y="{y + 15}" font-family="{MONO}" font-size="12" font-weight="600" fill="{p["text"]}" xml:space="preserve">{esc(sym[:26])}</text>\n'
              f'    <text x="270" y="{y + 15}" font-family="{MONO}" font-size="10.5" fill="{p["muted"]}" xml:space="preserve">{esc(desc)}</text>\n'
              f'    <text x="{W - 90}" y="{y + 15}" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{p["text"]}" xml:space="preserve">{esc(qty)}</text>\n'
              f'    <text x="{W - 18}" y="{y + 15}" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{p["dim"]}" xml:space="preserve">{esc(when)}</text>\n'
              f'  </g>\n')
    s += "</svg>\n"
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="HimanshuJ16")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--skills-repo", default="HimanshuJ16/Algo-Trading-Skills")
    a = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    now = dt.datetime.now(dt.timezone.utc)
    fills, stats = [], {}
    try:
        events = api(f"https://api.github.com/users/{a.user}/events/public?per_page=100", token)
        seen = set()
        for ev in events:
            f = to_fill(ev, now)
            if not f:
                continue
            key = (f[0], f[1], f[2])
            if key in seen:
                continue
            seen.add(key)
            fills.append(f)
            if len(fills) >= MAX_ROWS:
                break
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as e:
        print(f"events fetch failed: {e}", file=sys.stderr)
    try:
        u = api(f"https://api.github.com/users/{a.user}", token)
        stats["repos"] = u.get("public_repos", 0)
        stats["followers"] = u.get("followers", 0)
    except Exception as e:  # noqa: BLE001
        print(f"user fetch failed: {e}", file=sys.stderr)
    try:
        r = api(f"https://api.github.com/repos/{a.skills_repo}", token)
        stats["skills-repo ★"] = r.get("stargazers_count", 0)
    except Exception as e:  # noqa: BLE001
        print(f"repo fetch failed: {e}", file=sys.stderr)
    stamp = now.strftime("%d %b %Y %H:%M UTC")
    os.makedirs(a.out, exist_ok=True)
    for theme in PALETTES:
        path = os.path.join(a.out, f"blotter-{theme}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render(theme, fills, stats, stamp))
        print(f"wrote {path} ({len(fills)} fills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
