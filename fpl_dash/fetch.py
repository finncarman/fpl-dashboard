"""All network access. Stdlib only so it runs anywhere with Python 3.9+."""
import json
import re
import time
import urllib.request
import urllib.error
from html import unescape
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
FPL = "https://fantasy.premierleague.com/api"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def _get(url, headers=None, retries=3, timeout=30):
    hdrs = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed {url}: {last}")


def get_json(url, headers=None, cache_name=None):
    data = _get(url, headers)
    obj = json.loads(data)
    if cache_name:
        RAW.mkdir(parents=True, exist_ok=True)
        (RAW / cache_name).write_bytes(data)
    return obj


def get_text(url, headers=None):
    return _get(url, headers).decode("utf-8", "replace")


# ---------- FPL ----------
def bootstrap():
    return get_json(f"{FPL}/bootstrap-static/", cache_name="bootstrap.json")


def fixtures():
    return get_json(f"{FPL}/fixtures/", cache_name="fixtures.json")


def entry(entry_id):
    return get_json(f"{FPL}/entry/{entry_id}/")


def history(entry_id):
    return get_json(f"{FPL}/entry/{entry_id}/history/")


def picks(entry_id, gw):
    try:
        return get_json(f"{FPL}/entry/{entry_id}/event/{gw}/picks/")
    except RuntimeError:
        return None


def league(league_id, page=1):
    return get_json(f"{FPL}/leagues-classic/{league_id}/standings/?page_standings={page}")


# ---------- LiveFPL (public JSON used by livefpl.net) ----------
LF_HDR = {"Referer": "https://www.livefpl.net/", "Origin": "https://www.livefpl.net"}


def livefpl_prices():
    try:
        return get_json("https://livefpl.us/api/prices.json", LF_HDR)
    except Exception:
        return {}


def livefpl_top_transfers():
    try:
        return get_json("https://livefpl.us/top_transfers.json", LF_HDR)
    except Exception:
        return []


# ---------- Rotowire predicted / confirmed lineups ----------
def rotowire_lineups():
    """Returns list of {home, away, home_logo, away_logo, time, status, home_xi, away_xi}."""
    try:
        html = get_text("https://www.rotowire.com/soccer/lineups.php")
    except Exception:
        return []
    out = []
    for block in re.findall(r'<div class="lineup is-soccer.*?(?=<div class="lineup is-soccer|<div class="lineup__footer|$)', html, re.S):
        abbrs = re.findall(r'lineup__abbr">([^<]+)<', block)
        logos = re.findall(r'teamlogo/soccer/([^".?]+)', block)
        if len(abbrs) < 2:
            continue
        t = re.search(r'lineup__time">(.*?)</div>', block, re.S)
        time_txt = re.sub(r"<[^>]+>", "", t.group(1)).replace("&nbsp;", " ").strip() if t else ""
        sides = {}
        for side in ("home", "visit"):
            m = re.search(r'lineup__list is-%s">(.*?)</ul>' % side, block, re.S)
            if not m:
                sides[side] = ("", [], {})
                continue
            seg = m.group(1)
            st = re.search(r'lineup__status[^>]*>.*?</div>\s*([^<]+)', seg, re.S)
            status = st.group(1).strip() if st else ""
            # Rotowire lists the XI, then titled sections such as "Injuries" / "Substitutes".
            parts = re.split(r'<li class="lineup__title[^"]*">([^<]*)</li>', seg)
            groups = {"XI": parts[0]}
            for i in range(1, len(parts) - 1, 2):
                groups[parts[i].strip()] = parts[i + 1]
            def plist(chunk):
                return [(unescape(n).strip(), p.strip()) for p, n in re.findall(r'lineup__pos[^>]*>([^<]*)</div>\s*<a title="([^"]+)"', chunk)]
            sides[side] = (status, plist(groups["XI"]), {k: plist(v) for k, v in groups.items() if k != "XI"})
        out.append({
            "home": abbrs[0], "away": abbrs[1],
            "home_logo": logos[0] if logos else "", "away_logo": logos[1] if len(logos) > 1 else "",
            "time": time_txt,
            "home_status": sides["home"][0], "away_status": sides["visit"][0],
            "home_xi": sides["home"][1], "away_xi": sides["visit"][1],
            "home_extra": sides["home"][2], "away_extra": sides["visit"][2],
        })
    return out


# ---------- RSS ----------
def rss(url, limit=40):
    try:
        xml = get_text(url)
    except Exception:
        return []
    items = []
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S)[:limit]:
        def tag(name):
            m = re.search(r"<%s[^>]*>(.*?)</%s>" % (name, name), it, re.S)
            if not m:
                return ""
            v = m.group(1).strip()
            v = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", v, flags=re.S)
            return unescape(re.sub(r"<[^>]+>", "", v)).strip()
        items.append({"title": tag("title"), "link": tag("link"), "desc": tag("description")[:220], "date": tag("pubDate")})
    return items
