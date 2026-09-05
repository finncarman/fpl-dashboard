# FPL HQ

Personal Fantasy Premier League dashboard for team **3160882** (Yo Yo Yohanna). One static page, rebuilt on a schedule, readable on phone and laptop.

## What it shows
- **Brief** – deadline countdown, squad flags, lineup watch, price alerts on your players, top transfer thought, captain lean, mini league position.
- **Squad** – form, PPG, xGI/90, minutes security, ownership, explainable 3-GW projection, price-change progress, next 3 fixtures.
- **Transfers** – sell candidates with reasons (injury, fixtures, blanks, minutes, form, price drop, weak xGI) and 3 like-for-like buys within budget, each with reasons.
- **Captain** – ranked options for the next GW with the reasoning.
- **Prices** – LiveFPL price-change model: your players, likely risers/fallers tonight, what already changed, most popular transfers.
- **Injuries** – FPL official flags and news, sorted by ownership, your players highlighted.
- **Lineups** – Rotowire predicted/confirmed XIs, labelled with the FPL gameweek, your players highlighted.
- **Rivals** – each mini league: standings, gap to you, rival captains, chips and hits, what they own that you don't, your differentials.
- **Fixtures** – 6-GW FDR ticker sorted by easiest run.
- **Shortlist** – undervalued, nailed, low-owned picks per position, plus top projected per position.
- **News** – BBC and Guardian PL feeds, injury/fitness items separated.

## Run it locally
```bash
python3 build.py            # writes docs/index.html and docs/summary.json
python3 build.py --print    # also prints the Telegram-style summary
open docs/index.html
```
Python 3.9+, no dependencies.

## Hosting (free) – GitHub Pages + Actions
1. Create a **private** GitHub repo and push this folder.
2. Repo → Settings → Pages → Source: *Deploy from a branch*, branch `main`, folder `/docs`.
3. Repo → Settings → Actions → General → Workflow permissions: *Read and write*.
4. Actions tab → enable workflows. The schedule runs every 30 min; `build.py --gate` only rebuilds at ~8pm UK, within 6h of the deadline, or if the page is >26h old. Use *Run workflow* for an on-demand refresh.
5. Your page will be at `https://<user>.github.io/<repo>/`.

## Telegram summary (optional)
1. In Telegram, message **@BotFather** → `/newbot` → copy the token.
2. Message your new bot anything, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id`.
3. Repo → Settings → Secrets and variables → Actions: add secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and a variable `DASHBOARD_URL` with your Pages URL.

## Config
`config.json` – team id, mini leagues to watch (with how many rivals to fetch), news feeds, deadline window hours, daily build hour.

## Data sources
FPL public API · LiveFPL price/transfer JSON · Rotowire lineups · BBC & Guardian RSS. All free, no logins. Twitter is not automated (paid API); paste tweets into a Claude session for the final pre-deadline briefing.
