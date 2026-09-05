"""Static HTML dashboard. Mobile-first, dark, no dependencies."""
from html import escape as e
from datetime import timezone, timedelta

CSS = """
:root{--bg:#0f1218;--card:#171c26;--card2:#1e2433;--text:#e8ecf3;--muted:#8b94a7;--line:#2a3142;--green:#37e07c;--red:#ff5c6c;--amber:#ffc542;--blue:#5aa9ff;--purple:#b48bff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--blue);text-decoration:none}h1{font-size:22px;margin:0}h2{font-size:17px;margin:0 0 10px;display:flex;align-items:center;gap:8px}h3{font-size:14px;margin:12px 0 6px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.wrap{max-width:1180px;margin:0 auto;padding:14px}
.top{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;padding:6px 0 14px}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;background:var(--card2);color:var(--muted)}
.badge.g{background:rgba(55,224,124,.15);color:var(--green)}.badge.r{background:rgba(255,92,108,.15);color:var(--red)}.badge.a{background:rgba(255,197,66,.15);color:var(--amber)}.badge.b{background:rgba(90,169,255,.15);color:var(--blue)}.badge.p{background:rgba(180,139,255,.15);color:var(--purple)}
.nav{display:flex;gap:6px;flex-wrap:wrap;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5;border-bottom:1px solid var(--line)}
.nav a{padding:5px 10px;border-radius:8px;background:var(--card);font-size:13px;color:var(--text)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px;margin-top:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;overflow:hidden}
.card.wide{grid-column:1/-1}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px}
.stat{background:var(--card2);border-radius:10px;padding:8px 10px}.stat b{display:block;font-size:20px}.stat span{font-size:11px;color:var(--muted);text-transform:uppercase}
table{width:100%;border-collapse:collapse;font-size:13px}th{color:var(--muted);text-align:left;font-weight:600;padding:6px 6px;border-bottom:1px solid var(--line);white-space:nowrap}td{padding:6px 6px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border:0}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.fdr{display:inline-block;min-width:44px;text-align:center;border-radius:6px;padding:2px 4px;font-size:11px;font-weight:700;margin:1px}
.fdr1,.fdr2{background:#1e7a48;color:#dfffe9}.fdr3{background:#4b5563;color:#eee}.fdr4{background:#b3323f;color:#fff}.fdr5{background:#6b0f1a;color:#fff}.fdr0{background:#2a3142;color:var(--muted)}
.rsn{margin:4px 0 0 0;padding-left:18px;color:var(--muted);font-size:13px}.rsn li{margin:2px 0}
.sug{border-left:3px solid var(--red);padding:8px 10px;margin:10px 0;background:var(--card2);border-radius:0 10px 10px 0}
.buy{border-left:3px solid var(--green);padding:6px 10px;margin:6px 0 6px 12px;background:rgba(55,224,124,.06);border-radius:0 10px 10px 0}
.pl{font-weight:700}.pos{font-size:11px;color:var(--muted)}.muted{color:var(--muted)}.small{font-size:12px}
.cap{color:var(--amber);font-weight:800}.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden}.bar i{display:block;height:100%}
.pill{display:inline-block;background:var(--card2);border-radius:6px;padding:1px 6px;margin:1px;font-size:12px}
.pill.me{background:rgba(90,169,255,.2);color:var(--blue);font-weight:700}
.alert{background:rgba(255,92,108,.12);border:1px solid rgba(255,92,108,.35);border-radius:10px;padding:8px 10px;margin:8px 0}
.ok{background:rgba(55,224,124,.1);border:1px solid rgba(55,224,124,.3);border-radius:10px;padding:8px 10px;margin:8px 0}
.news li{margin:5px 0;font-size:13px}.news .src{color:var(--muted);font-size:11px;margin-right:6px}
details summary{cursor:pointer;color:var(--muted);font-size:13px}
footer{color:var(--muted);font-size:12px;padding:20px 0;text-align:center}
"""


def fdr_cell(run):
    out = []
    for r in run:
        if not r["games"]:
            out.append('<span class="fdr fdr0">BLANK</span>')
        else:
            for opp, ha, d in r["games"]:
                out.append(f'<span class="fdr fdr{d}">{opp} {ha}</span>')
    return "".join(out)


def pname(p, cap=False):
    s = f'<span class="pl">{e(p["name"])}</span> <span class="pos">{p["pos"]} {p["team_short"]} £{p["price"]:.1f}m</span>'
    if cap:
        s += ' <span class="cap">(C)</span>'
    return s


def flag_badge(p):
    if p["status"] == "a" and (p["chance"] is None or p["chance"] == 100):
        return ""
    cls = "a" if p["status"] == "d" or (p["chance"] or 0) >= 50 else "r"
    txt = f'{p["chance"]}%' if p["chance"] is not None else p["status_txt"]
    return f' <span class="badge {cls}" title="{e(p["news"])}">{txt}</span>'


def uk(dt):
    if not dt:
        return "?"
    # BST until last Sunday of Oct; good enough: UK offset by month
    off = 1 if 3 < dt.month < 11 else 0
    return (dt + timedelta(hours=off)).strftime("%a %d %b %H:%M") + (" BST" if off else " GMT")


def render(m):
    ent = m["entry"]
    h = []
    h.append(f'<title>FPL HQ · {e(ent["name"])}</title><style>{CSS}</style>')
    h.append('<div class="wrap">')
    dl = m["deadline"]
    htd = m["hours_to_deadline"]
    if htd is not None:
        if htd < 0:
            dl_txt = "deadline passed"
        elif htd < 24:
            dl_txt = f'{int(htd)}h {int((htd % 1) * 60)}m to GW{m["next_gw"]} deadline'
        else:
            dl_txt = f'{htd/24:.1f} days to GW{m["next_gw"]} deadline'
    else:
        dl_txt = "no upcoming deadline"
    dl_cls = "r" if htd is not None and 0 < htd < 12 else "a" if htd is not None and htd < 48 else "b"
    h.append(f'<div class="top"><div><h1>⚽ FPL HQ · {e(ent["name"])}</h1><div class="muted small">{e(ent["manager"])} · updated {uk(m["generated"])} · squad shown from GW{m["picks_gw"]}</div></div>'
             f'<div><span class="badge {dl_cls}">{dl_txt}</span> <span class="badge">{uk(dl)}</span></div></div>')
    h.append('<nav class="nav"><a href="#brief">Brief</a><a href="#squad">Squad</a><a href="#transfers">Transfers</a><a href="#captain">Captain</a><a href="#prices">Prices</a><a href="#injuries">Injuries</a><a href="#lineups">Lineups</a><a href="#rivals">Rivals</a><a href="#fixtures">Fixtures</a><a href="#shortlist">Shortlist</a><a href="#news">News</a></nav>')

    # ---- BRIEF ----
    h.append('<div class="grid"><div class="card wide" id="brief"><h2>📋 Tonight\'s brief</h2>')
    chips = ", ".join(f'{k} (GW{v})' for k, v in ent["chips_used"].items()) or "none"
    hist = ent["history"]
    last = hist[-1] if hist else {}
    h.append(f'<div class="stats"><div class="stat"><b>{ent["points"]}</b><span>Total pts</span></div><div class="stat"><b>{ent["overall_rank"]:,}</b><span>Overall rank</span></div>'
             f'<div class="stat"><b>{last.get("points","?")}</b><span>GW{m["cur_gw"]} pts</span></div><div class="stat"><b>£{ent["bank"]:.1f}m</b><span>In the bank</span></div>'
             f'<div class="stat"><b>£{ent["value"]:.1f}m</b><span>Team value</span></div><div class="stat"><b style="font-size:14px">{e(chips)}</b><span>Chips used</span></div></div>')
    if ent["active_chip"]:
        h.append(f'<div class="ok">Active chip this GW: <b>{e(ent["active_chip"])}</b></div>')
    flagged = [p for p in m["squad"] if flag_badge(p)]
    if flagged:
        h.append('<div class="alert"><b>Squad flags:</b> ' + ", ".join(f'{e(p["name"])} {flag_badge(p)} <span class="muted small">{e(p["news"])}</span>' for p in flagged) + "</div>")
    else:
        h.append('<div class="ok">No injury or suspension flags on your 15. ✅</div>')
    if m["my_lineup_alerts"]:
        h.append('<div class="alert"><b>Lineup watch (Rotowire):</b> ' + "; ".join(f'{e(a["player"]["name"])} not in {e(a["status"].lower() or "predicted")} XI vs {a["vs"]}' + (f' <span class="badge">GW{a["gw"]}</span>' if a["gw"] else "") for a in m["my_lineup_alerts"]) + "</div>")
    if m["my_price_alerts"]:
        h.append('<div class="alert"><b>Price alerts on your players tonight:</b> ' + ", ".join(f'{e(p["name"])} {"📈" if p["lf_tonight"]>0 else "📉"} {int(p["lf_tonight"]*100)}%' for p in m["my_price_alerts"]) + "</div>")
    if m["suggestions"]:
        s = m["suggestions"][0]
        b = s["buys"][0] if s["buys"] else None
        h.append(f'<p><b>Top transfer thought:</b> sell {pname(s["sell"]["player"])} → ' + (f'{pname(b["player"])} (+{b["delta"]:.1f} proj)' if b else "no clear upgrade in budget") +
                 f'<br><span class="muted small">Because: {e("; ".join(s["sell"]["reasons"]))}</span></p>')
    if m["captain"]:
        c = m["captain"][0]
        h.append(f'<p><b>Captain lean:</b> {pname(c["player"])} <span class="muted small">— {e(", ".join(c["why"]))}</span></p>')
    for lg in m["leagues"][:2]:
        me = next((r for r in lg["rivals"] if r["me"]), None)
        if me:
            ahead = [r for r in lg["rivals"] if r["gap"] > 0]
            behind = [r for r in lg["rivals"] if r["gap"] < 0]
            txt = f'you are {me["rank"]}{"st" if me["rank"]==1 else "nd" if me["rank"]==2 else "rd" if me["rank"]==3 else "th"}'
            if ahead:
                txt += f', {ahead[-1]["gap"]} behind {e(ahead[-1]["name"])}'
            if behind:
                txt += f', {-behind[0]["gap"]} ahead of {e(behind[0]["name"])}'
            h.append(f'<p class="small"><b>{e(lg["name"])}:</b> {txt}.</p>')
    h.append("</div>")

    # ---- SQUAD ----
    h.append('<div class="card wide" id="squad"><h2>👥 Your squad <span class="badge">GW' + str(m["picks_gw"]) + ' picks</span></h2><div class="scroll"><table><tr><th>#</th><th>Player</th><th class="num">Form</th><th class="num">PPG</th><th class="num">xGI/90</th><th class="num">Mins%</th><th class="num">Own%</th><th class="num">Proj</th><th class="num">Price Δ</th><th>Next 3</th></tr>')
    for p in sorted(m["squad"], key=lambda p: p["slot"]):
        row_cls = "" if p["starting"] else ' style="opacity:.6"'
        pc = p["lf_tonight"]
        pcs = f'<span class="{"badge g" if pc>0.6 else "badge r" if pc<-0.6 else "muted"}">{int(pc*100):+d}%</span>' if abs(pc) > 0.3 else '<span class="muted">–</span>'
        h.append(f'<tr{row_cls}><td class="muted">{p["slot"]}</td><td>{pname(p, p["is_captain"])}{" <span class=cap>(V)</span>" if p["is_vice"] else ""}{flag_badge(p)}</td>'
                 f'<td class="num">{p["form"]:.1f}</td><td class="num">{p["ppg"]:.1f}</td><td class="num">{p["xgi90"]:.2f}</td><td class="num">{int(p["mins_share"]*100)}</td><td class="num">{p["sel"]:.1f}</td>'
                 f'<td class="num"><b>{p["proj3"]:.1f}</b></td><td class="num">{pcs}</td><td>{fdr_cell(p["fixtures6"][:3])}</td></tr>')
    h.append('</table></div><p class="muted small">Proj = explainable 3-GW projection: 0.4×form + 0.3×PPG + 0.3×FPL ep_next, plus underlying (xGI/90 or xGC/90), plus fixture ease, scaled by availability and minutes security. It is a ranking tool, not a points forecast.</p></div>')

    # ---- TRANSFERS ----
    h.append('<div class="card wide" id="transfers"><h2>🔁 Transfer suggestions <span class="badge">£' + f'{ent["bank"]:.1f}' + 'm ITB</span></h2>')
    if not m["suggestions"]:
        h.append('<div class="ok">Nothing is screaming to be sold. Roll the transfer unless a price change forces your hand.</div>')
    for s in m["suggestions"]:
        sp = s["sell"]["player"]
        h.append(f'<div class="sug"><div>SELL {pname(sp)} <span class="badge">proj {sp["proj3"]:.1f}</span></div><ul class="rsn">' + "".join(f"<li>{e(r)}</li>" for r in s["sell"]["reasons"]) + "</ul>")
        if not s["buys"]:
            h.append('<div class="muted small" style="margin-left:12px">No like-for-like within budget who clears the availability and minutes filters.</div>')
        for b in s["buys"]:
            bp = b["player"]
            h.append(f'<div class="buy">BUY {pname(bp)} <span class="badge g">proj {bp["proj3"]:.1f} ({b["delta"]:+.1f})</span><ul class="rsn">' + "".join(f"<li>{e(w)}</li>" for w in b["why"]) + "</ul></div>")
        h.append("</div>")
    h.append('<p class="muted small">Buy prices use current price; your actual selling price may be lower if the player rose after you bought him. Options are filtered to available players with ≥65% minutes and ≤3 per club.</p></div>')

    # ---- CAPTAIN ----
    h.append('<div class="card" id="captain"><h2>©️ Captain options GW' + str(m["next_gw"]) + '</h2>')
    for i, c in enumerate(m["captain"]):
        h.append(f'<div style="margin:8px 0"><b>{i+1}.</b> {pname(c["player"])} <span class="badge {"a" if i==0 else ""}">score {c["score"]:.1f}</span><div class="muted small">{e(" · ".join(c["why"]))}</div></div>')
    h.append('<p class="muted small">Score = points form + xGI/90 + fixture ease for next GW only, scaled by availability.</p></div>')

    # ---- PRICES ----
    h.append('<div class="card" id="prices"><h2>💷 Price watch <span class="badge">LiveFPL</span></h2>')
    if m["my_price_alerts"]:
        h.append("<h3>Your players</h3>" + "".join(f'<div>{pname(p)} <span class="badge {"g" if p["lf_tonight"]>0 else "r"}">{int(p["lf_tonight"]*100):+d}% tonight</span></div>' for p in m["my_price_alerts"]))
    h.append('<h3>Likely risers tonight</h3><div class="scroll"><table>')
    for p in m["risers"]:
        pct = min(int(p["lf_tonight"] * 100), 130)
        h.append(f'<tr><td>{pname(p)}{" <span class=pill class=me>own</span>" if any(s["id"]==p["id"] for s in m["squad"]) else ""}</td><td style="width:38%"><div class="bar"><i style="width:{min(pct,100)}%;background:var(--green)"></i></div></td><td class="num">{pct}%</td></tr>')
    h.append('</table></div><h3>Likely fallers tonight</h3><div class="scroll"><table>')
    for p in m["fallers"]:
        pct = min(int(-p["lf_tonight"] * 100), 130)
        h.append(f'<tr><td>{pname(p)}</td><td style="width:38%"><div class="bar"><i style="width:{min(pct,100)}%;background:var(--red)"></i></div></td><td class="num">{pct}%</td></tr>')
    h.append("</table></div>")
    if m["changed_today"]:
        h.append('<h3>Changed already this GW</h3><div class="small">' + ", ".join(f'{e(p["name"])} {"📈" if p["cost_change_event"]>0 else "📉"} £{p["price"]:.1f}m' for p in sorted(m["changed_today"], key=lambda p:-p["sel"])[:20]) + "</div>")
    h.append('<h3>Most popular moves this GW</h3><div class="scroll"><table>')
    for t in m["top_transfers"]:
        h.append(f'<tr><td><span class="muted">OUT</span> {e(t["out"]["name"])} → <span class="muted">IN</span> {e(t["in"]["name"])}</td><td class="num">{t["count"]:,}</td></tr>')
    h.append('</table></div><p class="muted small">Progress is % of the way to a change by tonight\'s update (~01:30 UK). ≥100% means very likely.</p></div>')

    # ---- INJURIES ----
    h.append('<div class="card" id="injuries"><h2>🏥 Injuries & flags <span class="badge">FPL official</span></h2><div class="scroll"><table><tr><th>Player</th><th class="num">Own%</th><th>Status</th><th>News</th></tr>')
    for p in m["injuries"][:40]:
        mine = any(s["id"] == p["id"] for s in m["squad"])
        h.append(f'<tr{" style=background:rgba(90,169,255,.08)" if mine else ""}><td>{pname(p)}</td><td class="num">{p["sel"]:.1f}</td><td>{flag_badge(p) or e(p["status_txt"])}</td><td class="small">{e(p["news"])} <span class="muted">{p["news_added"]}</span></td></tr>')
    h.append("</table></div></div>")

    # ---- LINEUPS ----
    h.append('<div class="card wide" id="lineups"><h2>📋 Predicted / confirmed lineups <span class="badge">Rotowire</span></h2>')
    if not m["lineups"]:
        h.append('<p class="muted">No lineups published yet for the next round. Rotowire usually posts predicted XIs a few days out and confirmed XIs ~1h before kick-off.</p>')
    h.append('<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))">')
    for L in m["lineups"]:
        def side(s):
            st = s["status"]
            cls = "g" if "onfirm" in st else "a" if st else ""
            xi = ", ".join(f'<span class="pill{" me" if any(n.split()[-1].lower() in mn.lower() or mn.lower() in n.lower() for mn in s["mine"]) else ""}">{e(n)}</span>' for n in s["xi"]) or '<span class="muted">not yet</span>'
            return f'<div><b>{s["team"]}</b> <span class="badge {cls}">{e(st or "TBC")}</span><div class="small" style="margin-top:4px">{xi}</div></div>'
        h.append(f'<div class="card" style="padding:10px"><div class="muted small">{e(L["time"])}' + (f' · <b>GW{L["gw"]}</b>' if L["gw"] else "") + f'</div>{side(L["home"])}<div style="height:6px"></div>{side(L["away"])}</div>')
    h.append("</div></div>")

    # ---- RIVALS ----
    h.append('<div class="card wide" id="rivals"><h2>🥊 Mini league rival watch</h2><div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(340px,1fr))">')
    for lg in m["leagues"]:
        h.append(f'<div class="card" style="padding:10px"><h2 style="font-size:15px">{e(lg["name"])}</h2><div class="scroll"><table><tr><th>#</th><th>Manager</th><th class="num">Tot</th><th class="num">Gap</th><th>C</th><th>Owns that you don\'t</th></tr>')
        for r in lg["rivals"]:
            style = ' style="background:rgba(90,169,255,.12)"' if r["me"] else ""
            gap = "" if r["me"] else f'{r["gap"]:+d}'
            chip = f' <span class="badge p">{e(r["chip"])}</span>' if r["chip"] else ""
            hits = f' <span class="badge r">-{r["hits"]}</span>' if r["hits"] else ""
            h.append(f'<tr{style}><td>{r["rank"]}</td><td><b>{e(r["name"])}</b><br><span class="muted small">{e(r["team"])}</span>{chip}{hits}</td><td class="num">{r["total"]}</td><td class="num">{gap}</td><td class="small">{e(r["captain"])}</td><td class="small">{"" if r["me"] else e(", ".join(r["diffs"]))}</td></tr>')
        h.append("</table></div>")
        if lg["threats"]:
            h.append('<h3>Threats (rivals own, you don\'t)</h3><div class="small">' + ", ".join(f'{e(t["player"]["name"])} <span class="muted">{t["pct"]}%</span>' for t in lg["threats"]) + "</div>")
        if lg["my_diffs"]:
            h.append('<h3>Your differentials here</h3><div class="small">' + ", ".join(f'{e(d["player"]["name"])} <span class="muted">({d["n"]} rivals)</span>' for d in lg["my_diffs"]) + "</div>")
        if lg["cap_counts"]:
            h.append('<h3>Rival captains this GW</h3><div class="small">' + ", ".join(f'{e(n)} ×{c}' for n, c in lg["cap_counts"]) + "</div>")
        h.append("</div>")
    h.append("</div></div>")

    # ---- FIXTURES ----
    h.append('<div class="card wide" id="fixtures"><h2>📅 Fixture ticker · next 6 <span class="badge">FPL FDR</span></h2><div class="scroll"><table><tr><th>Team</th>' + "".join(f'<th>GW{g}</th>' for g in range(m["next_gw"], m["next_gw"] + 6)) + '<th class="num">Avg</th></tr>')
    for t in m["fixture_table"]:
        h.append(f'<tr><td><b>{t["team"]}</b></td>' + "".join(f'<td>{fdr_cell([r])}</td>' for r in t["run"]) + f'<td class="num">{t["avg"]:.1f}</td></tr>')
    h.append("</table></div></div>")

    # ---- SHORTLIST ----
    h.append('<div class="card wide" id="shortlist"><h2>💎 Shortlist</h2><div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))">')
    h.append('<div><h3>Undervalued (proj per £m, <12% owned, nailed)</h3><div class="scroll"><table>')
    for pos in ("GKP", "DEF", "MID", "FWD"):
        for p in m["shortlist"][pos]:
            h.append(f'<tr><td>{pname(p)}</td><td class="num">{p["form"]:.1f} form</td><td class="num">{p["sel"]:.1f}%</td><td class="num"><b>{p["proj3"]:.1f}</b></td><td>{fdr_cell(p["fixtures6"][:3])}</td></tr>')
    h.append("</table></div></div>")
    h.append('<div><h3>Top projected by position</h3><div class="scroll"><table>')
    for pos in ("GKP", "DEF", "MID", "FWD"):
        for p in m["top_by_pos"][pos][:5]:
            mine = any(s["id"] == p["id"] for s in m["squad"])
            h.append(f'<tr{" style=background:rgba(90,169,255,.08)" if mine else ""}><td>{pname(p)}{flag_badge(p)}</td><td class="num">{p["form"]:.1f} form</td><td class="num">{p["sel"]:.1f}%</td><td class="num"><b>{p["proj3"]:.1f}</b></td><td>{fdr_cell(p["fixtures6"][:3])}</td></tr>')
    h.append("</table></div></div></div></div>")

    # ---- NEWS ----
    h.append('<div class="card wide" id="news"><h2>📰 News</h2><div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))"><div><h3>Injury & fitness</h3><ul class="news">')
    for n in m["injury_news"]:
        h.append(f'<li><span class="src">{e(n["source"])}</span><a href="{e(n["link"])}" target="_blank">{e(n["title"])}</a></li>')
    h.append('</ul></div><div><h3>Premier League</h3><ul class="news">')
    for n in m["other_news"]:
        h.append(f'<li><span class="src">{e(n["source"])}</span><a href="{e(n["link"])}" target="_blank">{e(n["title"])}</a></li>')
    h.append("</ul></div></div></div>")

    h.append("</div>")  # grid
    h.append(f'<footer>Data: FPL API · LiveFPL price model · Rotowire lineups · BBC/Guardian RSS. Built {uk(m["generated"])}. Not affiliated with the Premier League.</footer></div>')
    return "\n".join(h)
