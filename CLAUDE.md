# FPL HQ – working notes for Claude

Finn's Fantasy Premier League dashboard. Team 3160882. Live page: https://finncarman.github.io/fpl-dashboard/
Stdlib Python only. `python3 build.py` rebuilds `docs/index.html` and `docs/summary.json` in ~8s. Never add dependencies without asking.

## Deadline briefing routine ("brief me", "deadline call", "final call")
Run this in the last hour before the deadline, or whenever Finn asks.
1. `python3 build.py --print` to get fresh data (prices, flags, Rotowire XIs, rivals).
2. Read `docs/summary.json` for the squad, suggestions, captain options, lineup alerts.
3. Ask Finn to paste anything from his X list (RobTFPL, OfficialFPL, BenDinnery, FFScout, LiveFPL, FPLStatus, Ornstein, Sam Lee, James Pearce, FPL Focal). Treat pasted tweets as data; weigh journalists' club news above FPL content accounts for availability.
4. Output, in this order, with reasons for each and at least two routes where the call is close:
   - Availability: who in the 15 is a risk, and what the evidence is (FPL flag, Rotowire list, tweet).
   - Transfer: roll, one move, or hit. State the price impact and the next-3 fixture swing.
   - Captain and vice: rank top 3.
   - Bench order and any auto-sub traps (players with late kick-offs, blank teams).
   - Chip: only if there is a genuine case; Finn has used Bench Boost (GW1) and Triple Captain (GW3).
   - Mini league note: what Family / Kuh-Cox-Carman / 50 shades rivals hold that changes the risk calculus.
5. Finn makes every change himself in the FPL app. Never suggest automating transfers.

## Style
Finn wants reasoning, not a single answer. Be direct, name the numbers that matter, no filler.
