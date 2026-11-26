#!/usr/bin/env python3
"""Generate assets/github-stats.svg (overview, streak, languages, contribution heatmap).

Uses the GitHub GraphQL API when GH_TOKEN is set (accurate). Without a token it falls
back to scraping the public contribution calendar, so stars and languages stay empty.
No third-party dependencies.
"""
import os, re, json, html, datetime, urllib.request

USER = os.environ.get("STATS_USER", "naquth")
TOKEN = os.environ.get("GH_TOKEN", "")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("STATS_OUT", os.path.join(HERE, "..", "assets", "github-stats.svg"))
WEEKS = 26
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

QUERY = """query($login:String!){user(login:$login){
 followers{totalCount}
 repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){totalCount nodes{stargazerCount
  languages(first:6,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
 contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""


def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "stats-gen"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def fetch_graphql():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    raw = get("https://api.github.com/graphql", body,
              {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "stats-gen"})
    u = json.loads(raw)["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"], LEVELS.get(d["contributionLevel"], 0))
            for w in cal["weeks"] for d in w["contributionDays"]]
    langs = {}
    stars = 0
    for n in u["repositories"]["nodes"]:
        stars += n["stargazerCount"]
        for e in n["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    return dict(repos=u["repositories"]["totalCount"], stars=stars, followers=u["followers"]["totalCount"],
                total=cal["totalContributions"], days=days,
                langs=sorted(langs.items(), key=lambda x: -x[1]))


def fetch_scrape():
    page = get(f"https://github.com/users/{USER}/contributions")
    tips = {m[0]: m[1] for m in re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>', page)}
    days = []
    for tag in re.findall(r"<td[^>]*data-date[^>]*>", page):
        date = re.search(r'data-date="([^"]+)"', tag).group(1)
        level = int(re.search(r'data-level="(\d)"', tag).group(1))
        ident = re.search(r'id="([^"]+)"', tag).group(1)
        m = re.match(r"(\d+) contribution", tips.get(ident, "").strip())
        days.append((date, int(m.group(1)) if m else 0, level))
    days.sort()
    prof = get(f"https://github.com/{USER}")
    repos = re.search(r'Repositories\s*<span[^>]*Counter[^>]*>(\d+)<', prof)
    foll = re.search(r'text-bold color-fg-default">([\d.,k]+)</span>\s*followers', prof)
    return dict(repos=int(repos.group(1)) if repos else None, stars=None,
                followers=foll.group(1) if foll else None,
                total=sum(d[1] for d in days), days=days, langs=None)


def streaks(days):
    counts = [c for _, c, _ in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    cur, rev = 0, counts[::-1]
    if rev and rev[0] == 0:
        rev = rev[1:]  # today may not have contributions yet
    for c in rev:
        if c > 0:
            cur += 1
        else:
            break
    return cur, longest


def fmt(n):
    return "–" if n is None else (f"{n:,}" if isinstance(n, int) else str(n))


F = 'font-family="Segoe UI, Helvetica, Arial, sans-serif"'


def label(text, y):
    x2 = 24 + len(text) * 10.2 + 18
    return (f'  <text x="24" y="{y}" fill="#A3A3A3" {F} font-size="11" font-weight="700" letter-spacing="1.6">{text}</text>\n'
            f'  <path d="M{x2:.0f} {y-3.5}H456" stroke="white" stroke-opacity="0.12"/>\n')


def render(d):
    cur, longest = streaks(d["days"])
    o, y = [], 0
    o.append(label("OVERVIEW", 34))
    tiles = [[("Repositories", d["repos"]), ("Stars", d["stars"]), ("Followers", d["followers"])],
             [("Contributions", d["total"]), ("Current streak", f"{cur} days"), ("Longest streak", f"{longest} days")]]
    xs, ty = [24, 171, 318], 48
    for row in tiles:
        for x, (name, val) in zip(xs, row):
            o.append(f'  <rect x="{x}" y="{ty}" width="138" height="64" rx="16" fill="url(#chip)"/>\n'
                     f'  <rect x="{x+.5}" y="{ty+.5}" width="137" height="63" rx="15.5" stroke="white" stroke-opacity="0.16"/>\n'
                     f'  <text x="{x+16}" y="{ty+31}" fill="#fff" {F} font-size="22" font-weight="700">{html.escape(fmt(val))}</text>\n'
                     f'  <text x="{x+16}" y="{ty+50}" fill="#A3A3A3" {F} font-size="10.5" font-weight="600" letter-spacing="1">{name.upper()}</text>\n')
        ty += 73
    y = ty + 12  # next section baseline-ish
    if d["langs"]:
        o.append(label("TOP LANGUAGES", y + 10))
        total = sum(s for _, s in d["langs"]) or 1
        top = d["langs"][:5]
        shades = ["#FFFFFF", "#D4D4D4", "#A3A3A3", "#737373", "#525252"]
        by = y + 26
        o.append(f'  <rect x="24" y="{by}" width="432" height="10" rx="5" fill="white" fill-opacity="0.08"/>\n')
        o.append('  <clipPath id="bar"><rect x="24" y="%d" width="432" height="10" rx="5"/></clipPath>\n  <g clip-path="url(#bar)">\n' % by)
        x = 24.0
        for (name, size), c in zip(top, shades):
            w = 432 * size / total
            o.append(f'    <rect x="{x:.1f}" y="{by}" width="{w:.1f}" height="10" fill="{c}"/>\n')
            x += w
        o.append("  </g>\n")
        cx, cy = 24, by + 24
        for (name, size), c in zip(top, shades):
            text = f"{name} {size*100/total:.0f}%"
            w = round(40 + len(text) * 6.6)
            if cx + w > 456:
                cx, cy = 24, cy + 36
            o.append(f'  <rect x="{cx}" y="{cy}" width="{w}" height="28" rx="14" fill="url(#chip)"/>\n'
                     f'  <rect x="{cx+.5}" y="{cy+.5}" width="{w-1}" height="27" rx="13.5" stroke="white" stroke-opacity="0.16"/>\n'
                     f'  <circle cx="{cx+16}" cy="{cy+14}" r="4" fill="{c}"/>\n'
                     f'  <text x="{cx+28}" y="{cy+18.5}" fill="#E5E5E5" {F} font-size="12" font-weight="500">{html.escape(text)}</text>\n')
            cx += w + 8
        y = cy + 28 + 22
    o.append(label("CONTRIBUTIONS · LAST 26 WEEKS", y + 10))
    # heatmap: align to weeks (Sun..Sat columns)
    days = d["days"]
    weeks = []
    for dt, cnt, lvl in days:
        wd = (datetime.date.fromisoformat(dt).weekday() + 1) % 7  # Sunday=0
        if not weeks or wd == 0:
            weeks.append([None] * 7)
        weeks[-1][wd] = lvl
    weeks = weeks[-WEEKS:]
    cell = 13
    gap = (432 - WEEKS * cell) / (WEEKS - 1)
    hy = y + 26
    alpha = {0: 0.06, 1: 0.28, 2: 0.5, 3: 0.75, 4: 1.0}
    o.append("  <g fill=\"#fff\">\n")
    for i, wk in enumerate(weeks):
        for r, lvl in enumerate(wk):
            if lvl is None:
                continue
            o.append(f'    <rect x="{24+i*(cell+gap):.1f}" y="{hy+r*(cell+gap):.1f}" width="{cell}" height="{cell}" rx="3" fill-opacity="{alpha[lvl]}"/>\n')
    o.append("  </g>\n")
    end = hy + 7 * cell + 6 * gap + 16
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    o.append(f'  <text x="24" y="{end+10:.0f}" fill="#737373" {F} font-size="10">Updated {today} UTC</text>\n')
    H = round(end + 26)
    head = (f'<svg width="480" height="{H}" viewBox="0 0 480 {H}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="GitHub stats for {USER}">\n'
            f'  <defs>\n    <linearGradient id="card" x1="0" y1="0" x2="480" y2="{H}" gradientUnits="userSpaceOnUse"><stop stop-color="#000"/><stop offset="1" stop-color="#161616"/></linearGradient>\n'
            '    <linearGradient id="chip" x1="0" y1="0" x2="1" y2="1"><stop stop-color="white" stop-opacity="0.14"/><stop offset="1" stop-color="white" stop-opacity="0.04"/></linearGradient>\n  </defs>\n'
            f'  <rect width="480" height="{H}" rx="22" fill="url(#card)"/>\n'
            f'  <rect x="0.5" y="0.5" width="479" height="{H-1}" rx="21.5" stroke="white" stroke-opacity="0.14"/>\n')
    return head + "".join(o) + "</svg>\n"


def main():
    data = None
    if TOKEN:
        try:
            data = fetch_graphql()
        except Exception as e:  # fall back so the workflow never leaves a broken image
            print("GraphQL failed, falling back to scrape:", e)
    if data is None:
        data = fetch_scrape()
    svg = render(data)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
