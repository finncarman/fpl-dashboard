"""Turns raw FPL / LiveFPL / Rotowire / RSS data into an explainable model dict."""
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone

from . import fetch

POS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
STATUS = {"a": "Available", "d": "Doubtful", "i": "Injured", "s": "Suspended", "u": "Unavailable", "n": "Not in squad"}
INJURY_WORDS = re.compile(r"injur|ruled out|doubt|fitness|blow|scan|knock|hamstring|suspend|ban|sidelined|miss|return|surgery|ankle|knee|calf|groin|thigh|concuss|illness|ill\b|absent|out for", re.I)


def f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


def build(cfg):
    now = datetime.now(timezone.utc)
    bs = fetch.bootstrap()
    fx = fetch.fixtures()
    entry_id = cfg["entry_id"]
    ent = fetch.entry(entry_id)
    hist = fetch.history(entry_id)

    events = bs["events"]
    cur_ev = next((e for e in events if e["is_current"]), None)
    next_ev = next((e for e in events if e["is_next"]), None)
    # After the last deadline but before the GW finishes, "current" is the live GW.
    cur_gw = cur_ev["id"] if cur_ev else (next_ev["id"] - 1 if next_ev else 1)
    next_gw = next_ev["id"] if next_ev else cur_gw
    deadline = datetime.fromisoformat(next_ev["deadline_time"].replace("Z", "+00:00")) if next_ev else None
    hours_to_deadline = (deadline - now).total_seconds() / 3600 if deadline else None

    teams = {t["id"]: t for t in bs["teams"]}
    tshort = {t["id"]: t["short_name"] for t in bs["teams"]}

    # ----- fixtures per team -----
    played = Counter()
    upcoming = defaultdict(lambda: defaultdict(list))  # team -> gw -> [(opp, H/A, fdr)]
    for m in fx:
        if m["finished"]:
            played[m["team_h"]] += 1
            played[m["team_a"]] += 1
        if m["event"] and m["event"] >= next_gw:
            upcoming[m["team_h"]][m["event"]].append((tshort[m["team_a"]], "H", m["team_h_difficulty"]))
            upcoming[m["team_a"]][m["event"]].append((tshort[m["team_h"]], "A", m["team_a_difficulty"]))

    def fixture_run(team, n):
        run = []
        for gw in range(next_gw, next_gw + n):
            run.append({"gw": gw, "games": upcoming[team].get(gw, [])})
        return run

    def avg_fdr(team, n):
        vals = []
        for gw in range(next_gw, next_gw + n):
            games = upcoming[team].get(gw, [])
            if not games:
                vals.append(5.5)  # blank is worse than a hard fixture
            for _, _, d in games:
                vals.append(d - (0.6 if len(games) > 1 else 0))  # small bonus for doubles
        return sum(vals) / max(len(vals), 1)

    # ----- external -----
    lf_prices = fetch.livefpl_prices()
    lf_tt = fetch.livefpl_top_transfers()
    lineups = fetch.rotowire_lineups()
    news_items = []
    for feed in cfg.get("news_feeds", []):
        for it in fetch.rss(feed["url"]):
            it["source"] = feed["name"]
            news_items.append(it)

    # ----- players -----
    players = {}
    for p in bs["elements"]:
        t = p["team"]
        mins = p["minutes"]
        games = max(played[t], 1)
        per90 = 90.0 / mins if mins >= 45 else 0.0
        xgi = f(p.get("expected_goal_involvements"))
        lf = lf_prices.get(str(p["id"]), {})
        d = {
            "id": p["id"], "name": p["web_name"], "full": f'{p["first_name"]} {p["second_name"]}',
            "team": t, "team_short": tshort[t], "pos": POS[p["element_type"]], "pos_id": p["element_type"],
            "price": p["now_cost"] / 10, "sel": f(p["selected_by_percent"]), "form": f(p["form"]),
            "ppg": f(p["points_per_game"]), "pts": p["total_points"], "mins": mins,
            "mins_share": min(mins / (games * 90.0), 1.0), "starts": p.get("starts", 0),
            "xg": f(p.get("expected_goals")), "xa": f(p.get("expected_assists")), "xgi": xgi,
            "xgi90": xgi * per90, "xgc": f(p.get("expected_goals_conceded")),
            "xgc90": f(p.get("expected_goals_conceded")) * per90,
            "goals": p["goals_scored"], "assists": p["assists"], "cs": p["clean_sheets"],
            "bonus": p["bonus"], "ep_next": f(p.get("ep_next")), "status": p["status"],
            "status_txt": STATUS.get(p["status"], p["status"]), "news": p.get("news") or "",
            "news_added": (p.get("news_added") or "")[:10],
            "chance": p.get("chance_of_playing_next_round"),
            "tin": p.get("transfers_in_event", 0), "tout": p.get("transfers_out_event", 0),
            "cost_change_event": p.get("cost_change_event", 0),
            "cost_change_start": p.get("cost_change_start", 0),
            "lf_progress": f(lf.get("progress")), "lf_tonight": f(lf.get("progress_tonight")),
            "lf_per_hour": f(lf.get("per_hour")),
            "fdr3": avg_fdr(t, 3), "fdr6": avg_fdr(t, 6), "fixtures6": fixture_run(t, 6),
        }
        d["net_transfers"] = d["tin"] - d["tout"]
        # ---- projection (explainable) ----
        base = 0.4 * d["form"] + 0.3 * d["ppg"] + 0.3 * d["ep_next"]
        under = 0.0
        if d["pos"] in ("MID", "FWD"):
            under = d["xgi90"] * 2.5
        elif d["pos"] == "DEF":
            under = max(0.0, (1.4 - d["xgc90"])) * 1.2 + d["xgi90"] * 2.0
        elif d["pos"] == "GKP":
            under = max(0.0, (1.4 - d["xgc90"])) * 1.2
        fix = (3.0 - d["fdr3"]) * 0.45
        raw = base + under + fix
        avail = 1.0
        if d["status"] in ("i", "s", "u", "n"):
            avail = 0.0 if d["chance"] in (None, 0) else d["chance"] / 100
        elif d["chance"] is not None and d["chance"] < 100:
            avail = d["chance"] / 100
        mins_pen = 1.0
        if played[t] >= 2 and d["mins_share"] < 0.6:
            mins_pen = 0.55 + 0.45 * d["mins_share"]
        d["proj3"] = round(max(raw, 0) * avail * mins_pen, 2)
        d["proj_parts"] = {"base": round(base, 2), "underlying": round(under, 2), "fixtures": round(fix, 2),
                           "availability": avail, "minutes_factor": round(mins_pen, 2)}
        d["value"] = round(d["proj3"] / d["price"], 3)
        players[p["id"]] = d

    def fix_str(pl, n=3):
        parts = []
        for r in pl["fixtures6"][:n]:
            if not r["games"]:
                parts.append("BLANK")
            else:
                parts.append("+".join(f"{o}({ha})" for o, ha, _ in r["games"]))
        return " ".join(parts)

    # ----- my squad -----
    picks_gw = cur_gw
    pk = fetch.picks(entry_id, picks_gw)
    if not pk and cur_gw > 1:
        picks_gw = cur_gw - 1
        pk = fetch.picks(entry_id, picks_gw)
    my_ids = set()
    squad = []
    if pk:
        for s in pk["picks"]:
            pl = dict(players[s["element"]])
            pl.update({"slot": s["position"], "multiplier": s["multiplier"], "is_captain": s["is_captain"],
                       "is_vice": s["is_vice_captain"], "starting": s["position"] <= 11})
            squad.append(pl)
            my_ids.add(s["element"])
    bank = (pk["entry_history"]["bank"] if pk else ent.get("last_deadline_bank", 0)) / 10
    value = (pk["entry_history"]["value"] if pk else ent.get("last_deadline_value", 0)) / 10
    chips_used = {c["name"]: c["event"] for c in hist.get("chips", [])}
    team_counts = Counter(p["team"] for p in squad)

    # ----- transfer suggestions -----
    sells = []
    for pl in squad:
        reasons = []
        sev = 0
        if pl["status"] != "a" or (pl["chance"] is not None and pl["chance"] < 100):
            reasons.append(f'{pl["status_txt"]}: {pl["news"] or "flagged"}' + (f' ({pl["chance"]}% chance)' if pl["chance"] is not None else ""))
            sev += 3 if pl["status"] in ("i", "s", "u", "n") else 2
        if pl["fdr3"] >= 3.6:
            reasons.append(f'tough run next 3: {fix_str(pl)} (avg FDR {pl["fdr3"]:.1f})')
            sev += 1
        if any(not r["games"] for r in pl["fixtures6"][:2]):
            reasons.append("blank gameweek coming")
            sev += 2
        if played[pl["team"]] >= 2 and pl["mins_share"] < 0.6:
            reasons.append(f'minutes risk: {int(pl["mins_share"]*100)}% of available minutes')
            sev += 2
        if pl["form"] < 2.5 and pl["price"] >= 6.0:
            reasons.append(f'poor form ({pl["form"]:.1f}) for a {pl["price"]:.1f}m player')
            sev += 1
        if pl["lf_tonight"] <= -0.75:
            reasons.append(f'price fall risk tonight ({int(pl["lf_tonight"]*100)}% of the way to a drop)')
            sev += 1
        if pl["pos"] in ("MID", "FWD") and pl["mins"] >= 180 and pl["xgi90"] < 0.2 and pl["price"] >= 6.5:
            reasons.append(f'weak underlying numbers (xGI/90 {pl["xgi90"]:.2f})')
            sev += 1
        if reasons:
            sells.append({"player": pl, "reasons": reasons, "severity": sev})
    sells.sort(key=lambda s: (-s["severity"], s["player"]["proj3"]))

    def buy_options(sell_pl, budget, n=3):
        opts = []
        for c in players.values():
            if c["pos_id"] != sell_pl["pos_id"] or c["id"] in my_ids or c["price"] > budget:
                continue
            if c["status"] != "a" or (c["chance"] is not None and c["chance"] < 100):
                continue
            if played[c["team"]] >= 2 and c["mins_share"] < 0.65:
                continue
            tc = team_counts[c["team"]] - (1 if c["team"] == sell_pl["team"] else 0)
            if tc >= 3:
                continue
            opts.append(c)
        opts.sort(key=lambda c: -c["proj3"])
        out = []
        for c in opts[:n]:
            why = [f'form {c["form"]:.1f}, {c["ppg"]:.1f} ppg']
            if c["pos"] in ("MID", "FWD"):
                why.append(f'xGI/90 {c["xgi90"]:.2f}')
            else:
                why.append(f'xGC/90 {c["xgc90"]:.2f}')
            why.append(f'next 3: {fix_str(c)} (FDR {c["fdr3"]:.1f})')
            why.append(f'{c["sel"]:.1f}% owned' + (" (differential)" if c["sel"] < 10 else " (template)" if c["sel"] > 30 else ""))
            if c["lf_tonight"] >= 0.75:
                why.append(f'price rise likely tonight ({int(c["lf_tonight"]*100)}%), buy before it goes up')
            if c["net_transfers"] > 50000:
                why.append(f'{c["net_transfers"]//1000}k net transfers in this GW')
            out.append({"player": c, "why": why, "delta": round(c["proj3"] - sell_pl["proj3"], 2)})
        return out

    suggestions = []
    for s in sells[:5]:
        budget = s["player"]["price"] + bank
        suggestions.append({"sell": s, "buys": buy_options(s["player"], budget)})

    # ----- captain -----
    cap = []
    for pl in squad:
        if not pl["starting"]:
            continue
        nxt = pl["fixtures6"][0]["games"]
        if not nxt:
            continue
        fdr1 = sum(d for _, _, d in nxt) / len(nxt)
        score = (0.5 * pl["form"] + 0.5 * pl["ppg"]) + pl["xgi90"] * 3 + (3 - fdr1) * 0.6 + (1.5 if len(nxt) > 1 else 0)
        avail = pl["proj_parts"]["availability"]
        score *= avail
        why = [f'{fix_str(pl,1)} FDR {fdr1:.0f}', f'form {pl["form"]:.1f}', f'xGI/90 {pl["xgi90"]:.2f}']
        if len(nxt) > 1:
            why.append("DOUBLE gameweek")
        if avail < 1:
            why.append(f'availability {int(avail*100)}%')
        cap.append({"player": pl, "score": round(score, 2), "why": why})
    cap.sort(key=lambda c: -c["score"])

    # ----- price watch -----
    all_pl = list(players.values())
    risers = sorted([p for p in all_pl if p["lf_tonight"] > 0.5], key=lambda p: -p["lf_tonight"])[:12]
    fallers = sorted([p for p in all_pl if p["lf_tonight"] < -0.5], key=lambda p: p["lf_tonight"])[:12]
    my_price_alerts = [p for p in squad if abs(p["lf_tonight"]) >= 0.6]
    changed_today = [p for p in all_pl if p["cost_change_event"] != 0 and p["sel"] > 1]
    top_transfers = []
    for row in lf_tt[:12]:
        try:
            o, i = players[row[0]], players[row[1]]
            top_transfers.append({"out": o, "in": i, "count": int(row[2])})
        except (KeyError, IndexError, TypeError):
            pass

    # ----- injuries -----
    injuries = sorted([p for p in all_pl if (p["status"] != "a" or p["news"]) and p["sel"] >= 1.0],
                      key=lambda p: -p["sel"])

    # ----- shortlist: undervalued -----
    shortlist = {}
    for pos in ("GKP", "DEF", "MID", "FWD"):
        cands = [p for p in all_pl if p["pos"] == pos and p["status"] == "a" and p["mins_share"] >= 0.7
                 and p["sel"] < 12 and p["id"] not in my_ids and played[p["team"]] >= 2]
        shortlist[pos] = sorted(cands, key=lambda p: -p["value"])[:5]
    top_by_pos = {pos: sorted([p for p in all_pl if p["pos"] == pos and p["mins_share"] >= 0.5], key=lambda p: -p["proj3"])[:8]
                  for pos in ("GKP", "DEF", "MID", "FWD")}

    # ----- lineups mapped to FPL -----
    rw_map = {}
    for t in bs["teams"]:
        rw_map[norm(t["name"])] = t["id"]
    lineup_view = []
    my_lineup_alerts = []
    fx_by_pair = {}
    for mfx in fx:
        if mfx.get("kickoff_time"):
            fx_by_pair.setdefault(frozenset((mfx["team_h"], mfx["team_a"])), []).append(mfx)
    MONTHS = {mn: i for i, mn in enumerate(["january","february","march","april","may","june","july","august","september","october","november","december"], 1)}

    def lineup_gw(h, a, time_txt):
        cands = fx_by_pair.get(frozenset((h, a)), [])
        mm = re.match(r"([A-Za-z]+)\s+(\d+)", time_txt or "")
        for c in cands:
            ko = datetime.fromisoformat(c["kickoff_time"].replace("Z", "+00:00"))
            if mm and MONTHS.get(mm.group(1).lower()) == ko.month and abs(int(mm.group(2)) - ko.day) <= 1:
                return c["event"]
        return cands[0]["event"] if cands else None

    for L in lineups:
        def team_id(logo, abbr):
            n = norm(logo)
            for k, v in rw_map.items():
                if k and (k in n or n in k):
                    return v
            for t in bs["teams"]:
                if t["short_name"] == abbr:
                    return t["id"]
            return None
        h, a = team_id(L["home_logo"], L["home"]), team_id(L["away_logo"], L["away"])
        if not h or not a:
            continue
        gw = lineup_gw(h, a, L["time"])
        sides = []
        for tid, xi, status in ((h, L["home_xi"], L["home_status"]), (a, L["away_xi"], L["away_status"])):
            names = {norm(n) for n, _ in xi}
            mine = [p for p in squad if p["team"] == tid]
            for p in mine:
                key_full, key_web = norm(p["full"]), norm(p["name"])
                hit = any(key_web and (key_web in nm or nm.endswith(key_web)) or key_full == nm for nm in names)
                if xi and not hit:
                    my_lineup_alerts.append({"player": p, "status": status.replace(" Lineup", ""), "gw": gw,
                                             "vs": tshort[a] if tid == h else tshort[h]})
            sides.append({"team": tshort[tid], "status": status, "xi": [n for n, _ in xi], "mine": [p["name"] for p in mine]})
        lineup_view.append({"time": L["time"], "gw": gw, "home": sides[0], "away": sides[1]})
    my_lineup_alerts.sort(key=lambda a: (-(a["gw"] or 0), a["player"]["slot"]))

    # ----- rivals -----
    leagues_view = []
    for lg in cfg.get("leagues", []):
        try:
            data = fetch.league(lg["id"])
        except RuntimeError:
            continue
        rows = data["standings"]["results"][: lg.get("top_n", 8)]
        me = next((r for r in data["standings"]["results"] if r["entry"] == entry_id), None)
        rivals = []
        owned = Counter()
        caps = Counter()
        for r in rows:
            rp = fetch.picks(r["entry"], picks_gw) if r["entry"] != entry_id else pk
            ids = [x["element"] for x in rp["picks"]] if rp else []
            capt = next((x["element"] for x in (rp["picks"] if rp else []) if x["is_captain"]), None)
            if r["entry"] != entry_id:
                for i in ids:
                    owned[i] += 1
                if capt:
                    caps[capt] += 1
            rivals.append({"rank": r["rank"], "name": r["player_name"], "team": r["entry_name"], "total": r["total"],
                           "gw": r["event_total"], "me": r["entry"] == entry_id,
                           "gap": r["total"] - (me["total"] if me else 0),
                           "captain": players[capt]["name"] if capt else "?",
                           "chip": rp.get("active_chip") if rp else None,
                           "hits": rp["entry_history"]["event_transfers_cost"] if rp else 0,
                           "diffs": [players[i]["name"] for i in ids if i not in my_ids][:6]})
        n_riv = max(len(rows) - 1, 1)
        threats = [{"player": players[i], "n": c, "pct": int(100 * c / n_riv)} for i, c in owned.most_common(40)
                   if i not in my_ids and c / n_riv >= 0.4][:8]
        mine_uniq = [{"player": players[i], "n": owned.get(i, 0)} for i in my_ids if owned.get(i, 0) / n_riv <= 0.25]
        mine_uniq.sort(key=lambda x: -x["player"]["proj3"])
        leagues_view.append({"name": lg["name"], "id": lg["id"], "rivals": rivals, "threats": threats,
                             "my_diffs": mine_uniq[:6], "cap_counts": [(players[i]["name"], c) for i, c in caps.most_common(3)],
                             "my_rank": me["rank"] if me else None, "size": data["standings"].get("results") and len(data["standings"]["results"])})

    # ----- news -----
    injury_news = [n for n in news_items if INJURY_WORDS.search(n["title"] + " " + n["desc"])][:14]
    other_news = [n for n in news_items if n not in injury_news][:10]

    return {
        "generated": now, "cur_gw": cur_gw, "next_gw": next_gw, "picks_gw": picks_gw, "deadline": deadline,
        "hours_to_deadline": hours_to_deadline,
        "entry": {"name": ent["name"], "manager": f'{ent["player_first_name"]} {ent["player_last_name"]}',
                  "overall_rank": ent["summary_overall_rank"], "points": ent["summary_overall_points"],
                  "gw_points": ent.get("summary_event_points"), "gw_rank": ent.get("summary_event_rank"),
                  "bank": bank, "value": value, "free_transfers": None, "chips_used": chips_used,
                  "history": hist.get("current", []), "active_chip": pk.get("active_chip") if pk else None},
        "squad": squad, "suggestions": suggestions, "sells": sells, "captain": cap[:4],
        "risers": risers, "fallers": fallers, "my_price_alerts": my_price_alerts, "changed_today": changed_today,
        "top_transfers": top_transfers, "injuries": injuries, "shortlist": shortlist, "top_by_pos": top_by_pos,
        "lineups": lineup_view, "my_lineup_alerts": my_lineup_alerts, "leagues": leagues_view,
        "injury_news": injury_news, "other_news": other_news, "teams": bs["teams"], "tshort": tshort,
        "fixture_table": [{"team": t["short_name"], "name": t["name"], "run": fixture_run(t["id"], 6), "avg": avg_fdr(t["id"], 6)}
                          for t in sorted(bs["teams"], key=lambda t: avg_fdr(t["id"], 6))],
        "fix_str": fix_str,
    }
