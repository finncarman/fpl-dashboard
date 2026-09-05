"""Telegram summary. Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars; silently skips otherwise."""
import json
import os
import urllib.request


def summary_text(m, url=None):
    ent = m["entry"]
    htd = m["hours_to_deadline"]
    L = [f'⚽ FPL HQ – {ent["name"]}']
    if htd is not None and htd > 0:
        L.append(f'⏰ GW{m["next_gw"]} deadline in {int(htd)}h {int((htd%1)*60)}m')
    L.append(f'Rank {ent["overall_rank"]:,} · {ent["points"]} pts · £{ent["bank"]:.1f}m ITB')
    flagged = [p for p in m["squad"] if p["status"] != "a" or (p["chance"] is not None and p["chance"] < 100)]
    if flagged:
        L.append("\n🏥 Flags: " + "; ".join(f'{p["name"]} ({p["chance"] if p["chance"] is not None else p["status_txt"]}{"%" if p["chance"] is not None else ""})' for p in flagged))
    if m["my_lineup_alerts"]:
        L.append("👀 Lineup watch: " + "; ".join(f'{a["player"]["name"]} {a["kind"]} ({a["status"].lower() or "predicted"}) vs {a["vs"]}' + (f' (GW{a["gw"]})' if a["gw"] else "") for a in m["my_lineup_alerts"]))
    if m["my_price_alerts"]:
        L.append("💷 Your prices tonight: " + ", ".join(f'{p["name"]} {"📈" if p["lf_tonight"]>0 else "📉"}{int(p["lf_tonight"]*100)}%' for p in m["my_price_alerts"]))
    if m["risers"]:
        L.append("📈 Risers: " + ", ".join(p["name"] for p in m["risers"][:6]))
    if m["fallers"]:
        L.append("📉 Fallers: " + ", ".join(p["name"] for p in m["fallers"][:6]))
    if m["suggestions"]:
        L.append("\n🔁 Transfer thoughts:")
        for s in m["suggestions"][:3]:
            sp = s["sell"]["player"]
            b = s["buys"][0]["player"]["name"] if s["buys"] else "no clear upgrade"
            L.append(f'• {sp["name"]} → {b}. {s["sell"]["reasons"][0]}')
    if m["captain"]:
        L.append("\n©️ Captain: " + " / ".join(f'{c["player"]["name"]} ({c["score"]:.1f})' for c in m["captain"][:3]))
    for lg in m["leagues"][:3]:
        me = next((r for r in lg["rivals"] if r["me"]), None)
        if me:
            L.append(f'🏆 {lg["name"]}: {me["rank"]}{"st" if me["rank"]==1 else "nd" if me["rank"]==2 else "rd" if me["rank"]==3 else "th"}')
    if url:
        L.append(f"\n{url}")
    return "\n".join(L)[:4000]


def send_telegram(text):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        return False
    body = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status == 200
