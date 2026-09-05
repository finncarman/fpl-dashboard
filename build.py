#!/usr/bin/env python3
"""Build the FPL dashboard.

  python3 build.py                 build docs/index.html now
  python3 build.py --notify        also send the Telegram summary (if env vars set)
  python3 build.py --gate          only build if in the 8pm window or near the deadline (for cron)
  python3 build.py --print         print the Telegram-style summary to stdout
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from fpl_dash import analyse, render, notify  # noqa: E402


def uk_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/London"))
    except Exception:
        return datetime.now(timezone.utc)


def should_run(cfg):
    """Cheap pre-check using only bootstrap deadline: 8pm UK window, or within N hours of deadline, or stale >26h."""
    from fpl_dash import fetch
    now = uk_now()
    stamp = ROOT / "data" / "last_build.txt"
    last = None
    if stamp.exists():
        try:
            last = datetime.fromisoformat(stamp.read_text().strip())
        except ValueError:
            pass
    age_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600 if last else 999
    if age_h > 26:
        return True, "stale"
    if now.hour == cfg.get("daily_build_hour_uk", 20) and now.minute < 35 and age_h > 1:
        return True, "daily window"
    bs = fetch.bootstrap()
    nxt = next((e for e in bs["events"] if e["is_next"]), None)
    if nxt:
        dl = datetime.fromisoformat(nxt["deadline_time"].replace("Z", "+00:00"))
        h = (dl - datetime.now(timezone.utc)).total_seconds() / 3600
        if 0 < h <= cfg.get("deadline_window_hours", 6):
            return True, f"deadline in {h:.1f}h"
    return False, f"outside window (last build {age_h:.1f}h ago)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "docs" / "index.html"))
    args = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text())
    if args.gate:
        ok, why = should_run(cfg)
        print(f"gate: {why}")
        if not ok:
            return 0
    model = analyse.build(cfg)
    html = render.render(model)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "last_build.txt").write_text(datetime.now(timezone.utc).isoformat())
    # small JSON export for other tools / the deadline briefing
    slim = {
        "generated": model["generated"].isoformat(), "next_gw": model["next_gw"], "deadline": model["deadline"].isoformat() if model["deadline"] else None,
        "entry": {k: v for k, v in model["entry"].items() if k != "history"},
        "squad": [{k: p[k] for k in ("name", "pos", "team_short", "price", "form", "xgi90", "mins_share", "sel", "proj3", "status", "news", "chance", "lf_tonight", "slot", "is_captain")} for p in model["squad"]],
        "suggestions": [{"sell": s["sell"]["player"]["name"], "reasons": s["sell"]["reasons"],
                         "buys": [{"name": b["player"]["name"], "why": b["why"], "delta": b["delta"]} for b in s["buys"]]} for s in model["suggestions"]],
        "captain": [{"name": c["player"]["name"], "score": c["score"], "why": c["why"]} for c in model["captain"]],
        "risers": [p["name"] for p in model["risers"]], "fallers": [p["name"] for p in model["fallers"]],
        "lineup_alerts": [{"player": a["player"]["name"], "status": a["status"], "vs": a["vs"]} for a in model["my_lineup_alerts"]],
    }
    (out.parent / "summary.json").write_text(json.dumps(slim, indent=1))
    text = notify.summary_text(model, os.environ.get("DASHBOARD_URL"))
    if args.print:
        print(text)
    if args.notify:
        have_tok = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
        have_chat = bool(os.environ.get("TELEGRAM_CHAT_ID"))
        if have_tok and have_chat:
            try:
                print("telegram:", "sent" if notify.send_telegram(text) else "failed")
            except Exception as ex:
                print("telegram: error", ex)
        else:
            print(f"telegram: skipped (TELEGRAM_BOT_TOKEN {'set' if have_tok else 'MISSING'}, TELEGRAM_CHAT_ID {'set' if have_chat else 'MISSING'})")
    print(f"built {out} ({len(html)//1024} KB), GW{model['next_gw']} deadline {model['deadline']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
