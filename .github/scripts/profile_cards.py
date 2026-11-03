#!/usr/bin/env python3
"""Generate animated profile cards (stats, languages, activity) as SVG.

Runs in GitHub Actions with GITHUB_TOKEN. Usage:
  python3 profile_cards.py <username> <out_dir> [--data sample.json]
"""
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from html import escape

ACCENT = "#36bcf7"
BG0, BG1 = "#0b1418", "#1d3a47"
TEXT, MUTED = "#c9eefe", "#6f97a8"
FONT = "'Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO = "Consolas,'Courier New',monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(login):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def fmt(n):
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def shell(w, h, body, extra_defs=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>
<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="{ACCENT}" stroke-opacity=".05"/></pattern>
<linearGradient id="beam" x1="0" x2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".5" stop-color="{ACCENT}"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
<style>
.t{{font:700 15px {MONO};fill:{ACCENT};letter-spacing:3px}}
.l{{font:400 14px {FONT};fill:{MUTED}}}
.v{{font:700 22px {FONT};fill:{TEXT}}}
.s{{font:400 12px {FONT};fill:{MUTED}}}
.f{{opacity:0;animation:in .6s ease-out forwards}}
@keyframes in{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
</style>
{extra_defs}
<clipPath id="card"><rect width="{w}" height="{h}" rx="16"/></clipPath>
</defs>
<g clip-path="url(#card)">
<rect width="{w}" height="{h}" fill="url(#bg)"/><rect width="{w}" height="{h}" fill="url(#grid)"/>
<rect y="{h-3}" width="160" height="3" fill="url(#beam)"><animate attributeName="x" values="-160;{w}" dur="4s" repeatCount="indefinite"/></rect>
{body}
</g>
<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="16" fill="none" stroke="{ACCENT}" stroke-opacity=".3"/>
</svg>"""


def icon(kind, x, y):
    c = f'stroke="{ACCENT}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    paths = {
        "star": "M9 1.5l2.3 4.7 5.2.8-3.8 3.7.9 5.2L9 13.4l-4.6 2.5.9-5.2L1.5 7l5.2-.8z",
        "commit": "M1 9h4.5M12.5 9H17M9 5.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7z",
        "pr": "M4 2v14M4 2a2 2 0 1 1 0 0M14 16a2 2 0 1 1 0 0M14 14V7a3 3 0 0 0-3-3H8M10 2L8 4l2 2",
        "issue": "M9 1.5a7.5 7.5 0 1 1 0 15 7.5 7.5 0 0 1 0-15zM9 5.5v4M9 12.5v.1",
        "repo": "M3 2.5A1.5 1.5 0 0 1 4.5 1H15v13H4.5A1.5 1.5 0 0 0 3 15.5zM3 15.5A1.5 1.5 0 0 0 4.5 17H15v-3",
        "people": "M6.5 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM1 16c0-3 2.5-5 5.5-5s5.5 2 5.5 5M12 2.2a3 3 0 0 1 0 5.6M14 11.3c1.8.6 3 2.2 3 4.7",
    }
    return f'<path transform="translate({x},{y})" d="{paths[kind]}" {c}/>'


def stats_card(u):
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    cc = u["contributionsCollection"]
    total = cc["contributionCalendar"]["totalContributions"]
    rows = [
        ("star", "Total Stars", stars),
        ("commit", "Commits (1 tahun)", cc["totalCommitContributions"]),
        ("pr", "Pull Requests", u["pullRequests"]["totalCount"]),
        ("issue", "Issues", u["issues"]["totalCount"]),
        ("repo", "Public Repos", u["repositories"]["totalCount"]),
        ("people", "Followers", u["followers"]["totalCount"]),
    ]
    body = [f'<text x="28" y="38" class="t">⌁ GITHUB STATS</text>']
    for i, (ic, label, val) in enumerate(rows):
        y = 70 + i * 30
        body.append(
            f'<g class="f" style="animation-delay:{0.15 + i*0.12:.2f}s">'
            f'{icon(ic, 28, y-13)}<text x="58" y="{y+1}" class="l">{label}</text>'
            f'<text x="300" y="{y+2}" class="v" text-anchor="end" style="font-size:16px">{fmt(val)}</text></g>'
        )
    # ring: contributions in the last year
    cx, cy, r = 400, 125, 56
    circ = 2 * 3.14159 * r
    frac = min(total / 1000, 1) if total else 0
    body.append(f"""<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{ACCENT}" stroke-opacity=".12" stroke-width="9"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{ACCENT}" stroke-width="9" stroke-linecap="round"
 stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ:.1f}" transform="rotate(-90 {cx} {cy})">
 <animate attributeName="stroke-dashoffset" from="{circ:.1f}" to="{circ*(1-max(frac,.04)):.1f}" dur="1.6s" begin=".3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/>
</circle>
<circle cx="{cx}" cy="{cy}" r="{r+14}" fill="none" stroke="{ACCENT}" stroke-opacity=".25" stroke-dasharray="2 8">
 <animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="30s" repeatCount="indefinite"/>
</circle>
<g class="f" style="animation-delay:.6s"><text x="{cx}" y="{cy+6}" class="v" text-anchor="middle" style="font-size:26px">{fmt(total)}</text>
<text x="{cx}" y="{cy+26}" class="s" text-anchor="middle">kontribusi</text></g>
<text x="{cx}" y="{cy+r+32}" class="s" text-anchor="middle">12 bulan terakhir</text>""")
    return shell(500, 260, "\n".join(body))


def languages_card(u):
    agg = defaultdict(int)
    colors = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            agg[n] += e["size"]
            colors[n] = e["node"]["color"] or ACCENT
    top = sorted(agg.items(), key=lambda x: -x[1])[:6]
    tot = sum(v for _, v in top) or 1
    body = [f'<text x="28" y="38" class="t">⌁ TOP LANGUAGES</text>']
    # stacked bar
    x, bw = 28, 444
    body.append(f'<clipPath id="bar"><rect x="28" y="58" width="{bw}" height="12" rx="6"/></clipPath><g clip-path="url(#bar)">')
    for name, v in top:
        w = bw * v / tot
        body.append(f'<rect x="{x:.1f}" y="58" width="0" height="12" fill="{colors[name]}"><animate attributeName="width" from="0" to="{w:.1f}" dur="1s" begin=".3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/></rect>')
        x += w
    body.append("</g>")
    if not top:
        body.append(f'<text x="250" y="140" class="l" text-anchor="middle">Belum ada data bahasa</text>')
    for i, (name, v) in enumerate(top):
        col, row = i % 2, i // 2
        px, py = 28 + col * 230, 108 + row * 46
        pct = 100 * v / tot
        body.append(
            f'<g class="f" style="animation-delay:{0.4 + i*0.1:.2f}s">'
            f'<circle cx="{px+6}" cy="{py-5}" r="6" fill="{colors[name]}"/>'
            f'<text x="{px+20}" y="{py}" class="l" style="fill:{TEXT}">{escape(name)}</text>'
            f'<text x="{px+210}" y="{py}" class="s" text-anchor="end">{pct:.1f}%</text>'
            f'<rect x="{px+20}" y="{py+9}" width="190" height="3" rx="1.5" fill="{ACCENT}" fill-opacity=".1"/>'
            f'<rect x="{px+20}" y="{py+9}" width="0" height="3" rx="1.5" fill="{colors[name]}"><animate attributeName="width" from="0" to="{190*pct/100:.1f}" dur="1s" begin="{0.5 + i*0.1:.2f}s" fill="freeze"/></rect></g>'
        )
    return shell(500, 260, "\n".join(body))


def activity_card(u):
    days = [d for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    days = days[-31:]
    W, H = 1000, 300
    left, right, top, bottom = 50, 30, 70, 50
    pw, ph = W - left - right, H - top - bottom
    vals = [d["contributionCount"] for d in days] or [0]
    mx = max(max(vals), 4)
    n = max(len(vals) - 1, 1)
    pts = [(left + pw * i / n, top + ph - ph * v / mx) for i, v in enumerate(vals)]

    def smooth(p):
        d = f"M{p[0][0]:.1f},{p[0][1]:.1f}"
        for i in range(1, len(p)):
            x0, y0 = p[i - 1]
            x1, y1 = p[i]
            cxm = (x0 + x1) / 2
            d += f" C{cxm:.1f},{y0:.1f} {cxm:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
        return d

    line = smooth(pts)
    area = line + f" L{pts[-1][0]:.1f},{top+ph} L{pts[0][0]:.1f},{top+ph} Z"
    defs = f"""<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".45"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
<filter id="glow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<clipPath id="reveal"><rect x="0" y="0" width="0" height="{H}"><animate attributeName="width" from="0" to="{W}" dur="2.2s" begin=".2s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .3 1"/></rect></clipPath>"""
    total = sum(vals)
    best = max(vals)
    active = sum(1 for v in vals if v)
    body = [f'<text x="{left}" y="38" class="t">⌁ ACTIVITY · 31 HARI TERAKHIR</text>']
    for j, (lab, val) in enumerate([("total", total), ("hari aktif", active), ("terbanyak/hari", best)]):
        x = W - right - j * 150
        body.append(f'<g class="f" style="animation-delay:{0.2+j*0.1:.1f}s"><text x="{x}" y="34" class="v" text-anchor="end" style="font-size:20px">{val}</text><text x="{x}" y="52" class="s" text-anchor="end">{lab}</text></g>')
    for k in range(5):
        y = top + ph * k / 4
        body.append(f'<line x1="{left}" x2="{W-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{ACCENT}" stroke-opacity=".08"/>')
        body.append(f'<text x="{left-10}" y="{y+4:.1f}" class="s" text-anchor="end">{round(mx*(4-k)/4)}</text>')
    body.append(f'<g clip-path="url(#reveal)"><path d="{area}" fill="url(#area)"/><path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="2.5" filter="url(#glow)"/>')
    for i, ((x, y), v) in enumerate(zip(pts, vals)):
        if v:
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#fff" stroke="{ACCENT}" stroke-width="2"/>')
    body.append("</g>")
    # pulse on last point
    lx, ly = pts[-1]
    body.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="5" fill="{ACCENT}"><animate attributeName="r" values="5;14;5" dur="2s" begin="2.4s" repeatCount="indefinite"/><animate attributeName="opacity" values=".8;0;.8" dur="2s" begin="2.4s" repeatCount="indefinite"/></circle>')
    for i in range(0, len(days), 5):
        dd = date.fromisoformat(days[i]["date"])
        body.append(f'<text x="{pts[i][0]:.1f}" y="{top+ph+24}" class="s" text-anchor="middle">{dd.day:02d}/{dd.month:02d}</text>')
    return shell(W, H, "\n".join(body), defs)


def main():
    login, out = sys.argv[1], sys.argv[2]
    if "--data" in sys.argv:
        with open(sys.argv[sys.argv.index("--data") + 1]) as f:
            u = json.load(f)
    else:
        u = fetch(login)
    os.makedirs(out, exist_ok=True)
    for name, fn in (("stats", stats_card), ("languages", languages_card), ("activity", activity_card)):
        with open(os.path.join(out, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(fn(u))
    print("cards written to", out)


if __name__ == "__main__":
    main()
