# MEMORY.md - Chad's Long-Term Memory

## Who I Am
- **Name:** Chad
- **Role:** Sam's autonomous trading bot
- **Emoji:** 🧠
- **Vibe:** Chill, sharp, hardworking, a little weird

## Who Sam Is
- **Name:** Sam
- **Timezone:** America/New_York
- **Style:** Brief, no-frills communicator, trader

---

## Commands

| Command | What It Does |
|---------|--------------|
| `/sta` | Quick: building tiers + open positions + P&L |
| `/sum` | Full day: all tiers by anchor hour + candle grid |

*(Avoid `/status` and `/summary` — clash with OpenClaw built-ins)*

**Anchor Hours:** 8am, 9am, 10am, 11am, 12pm, 1pm, 3pm, 5pm  
**Entry Hours:** 1pm, 3pm, 4pm, 5pm, 6pm, 7pm, 9pm, 11pm

**Auto Mode (cron):**
- Anchor hours → Alert on new anchors forming
- Entry hours → Alert + execute when signals fire
- Position held → Monitor for exits
- Between hours → HEARTBEAT_OK (silent)

---

## Trading Setup

### Strategy: Red Candle Mean Reversion v3.3 (25-Tier, Risk-Adjusted Kelly, 12x EVAL)
Buy after sustained selling pressure (consecutive red hourly candles), exit on bounce confirmation or time cap.

**Tier Naming:** `[Anchor][Trade][#]` — e.g., BS3 = BTC anchor → SOL trade, variant 3

**Execution Model (VERIFIED 2026-03-02):**
- Entry: OPEN price of entry hour
- Exit on 2 greens: OPEN of candle AFTER 2nd green confirms
- Exit on time cap: OPEN of candle AFTER cap expires
- Position sizing: Kelly-based (half-Kelly)
- **No look-ahead bias anywhere**

### Backtest Stats (25-Tier, Risk-Adjusted Kelly, 12x EVAL Scale)
| Metric | Value |
|--------|-------|
| Tiers | 25 (EE6 removed, 4 risk-adjusted) |
| Trades | 222 |
| Win Rate | **92.3%** (205W / 17L) |
| Total P&L | **$343,764** |
| Avg/Trade | **$1,548** |
| Best Trade | $+16,664 |
| Worst Trade | $-1,802 |
| Worst Day | $-1,802 |
| Buffer to $3K Bust | **$1,198** |

**Removed:** EE6 (66.7% WR too low)
**Risk-adjusted Kelly (reduced sizing for lower WR):**
- BS3: 0.32 → 0.16 (78% WR)
- EE4: 0.37 → 0.30 (80% WR)
- EE5: 0.20 → 0.16 (75% WR)
- ES4: 0.29 → 0.26 (79% WR)

### Scale Modes
| Mode | Base | Scale | Worst Day | Use When |
|------|------|-------|-----------|----------|
| **EVAL** | $264,000 | **12x** | $-1,802 | Passing prop eval |
| FUNDED | $220,000 | 10x | $-1,500 | After passing |

### Annual Performance (25 tiers, Risk-Adjusted Kelly, 12x Scale)
| Year | Trades | WR | P&L | Avg |
|------|--------|-----|---------|-----|
| 2022 | 89 | 89% | $+171,049 | $+1,922 |
| 2023 | 31 | 100% | $+38,944 | $+1,256 |
| 2024 | 53 | 92% | $+63,095 | $+1,191 |
| 2025 | 37 | 97% | $+51,122 | $+1,382 |
| 2026 | 12 | 83% | $+19,553 | $+1,629 |

### Position Sizing (12x EVAL Scale, Base $264K)
| Kelly | Position | BTC Lots | ETH Lots | SOL Lots |
|-------|----------|----------|----------|----------|
| 0.50 | $132,000 | 1.47 | 52.8 | 880 |
| 0.44 | $116,160 | 1.29 | 46.5 | 774 |
| 0.43 | $113,520 | 1.26 | 45.4 | 757 |
| 0.41 | $108,240 | 1.20 | 43.3 | 722 |
| 0.39 | $102,960 | 1.14 | 41.2 | 686 |
| 0.32 | $84,480 | 0.94 | 33.8 | 563 |
| 0.24 | $63,360 | 0.70 | 25.3 | 422 |
| 0.20 | $52,800 | 0.59 | 21.1 | 352 |
| 0.16 | $42,240 | 0.47 | 16.9 | 282 |

### Risk Controls
- **Daily exposure cap:** $2,500 (calculated at 4.56% worst case)
- **Buffer to bust:** $1,198 (prop limit is $3K)
- **Priority cascade:** First tier to fire claims asset
- **No stop-losses** — strategy proven without them

### P&L Tracking — REAL NUMBERS ONLY
**RULE:** Always use actual P&L from the live prop account (breakoutprop.com), NOT calculated/estimated numbers from bot state. Check the platform for real fills, real balance changes. Slippage and fees matter.

---

## Prop Account

**⚠️ See PROP_ACCOUNT.md for immutable rules ⚠️**

- **Platform:** breakoutprop.com
- **Account #:** REDACTED
- **Type:** Classic eval, 1 Step, $100K margin
- **Leverage:** BTC/ETH 5x, SOL 2x
- **Goal:** +$10,000 (10%)
- **Max DD:** -$6,000 (6%)
- **Daily Loss:** -$3,000 = **AUTO BREACH** ❌
- **Our Worst Day:** $-1,802 (buffer $1,198)
- **Daily reset:** 8pm EST

---

## Active Cron Jobs

1. **Signal Check v4.0 (25-tier, Kelly, 12x)** (id: `33c8ea68`)
   - Schedule: 9am-11pm EST (hourly at :01)
   - 9:01 checks 8am anchors, 10:01 checks 9am, etc.
   - **ANCHOR HOURS ONLY — NO NOISE:**
     - Only message Sam when anchor is building or signal pending
     - Silent when nothing developing
     - Never repeat "no signals" — Sam doesn't want spam
   - See "Anchor Update Format" below for message template

2. **Daily Trading Summary** (id: `9bed53a7`)
   - Schedule: 9pm EST daily

3. **Cancel Claude Subscription** (id: `f0f98aeb`)
   - Schedule: 10am EST, March 10-12

---

## Key Files

- `tools/eval.py` — Backtest simulator (26 tiers, Kelly, 12x)
- `tools/signal-check.py` — Live signal checker
- `tools/.bot-state.json` — Bot state (positions, trade log)
- `tools/mega-backtest-data-complete.json` — Historical OHLC
- `STRATEGY.md` — Full strategy documentation
- `PROP_ACCOUNT.md` — Immutable prop account rules

---

## Anchor Update Format — MANDATORY

**RULE: Every anchor alert MUST use this exact format. No shortcuts.**

```
📊 [TIME] Check — [DATE]

       8am 9am 10a 11a 12p 1pm 2pm 3pm ...
BTC     🔴  🟢  🟢  🔴  🟢  🔴  🔴  ⬜
ETH     🟢  🟢  🟢  🟢  🔴  🟢  ⬜  ⬜
SOL     🟢  🟢  🔴  🟢  🔴  🟢  ⬜  ⬜

❌ Dead ([X] tiers):
• [Summary of why tiers died - anchors green/too small]

⏳ Still possible:

| Tier | Anchor | Thresh | Need | Entry | WR | Avg PnL |
|------|--------|--------|------|-------|-----|---------|
| SB1  | SOL 3pm | >4.0% | 2+/3h reds | 6pm | 86% | +$1,280 |

🎯 Active: [status]
```

**Required elements:**
1. Candle grid (starting at 8am through current hour, all 3 assets)
2. Dead tiers count + summary
3. Still possible table with WR + Avg PnL columns
4. Active status line

**Do NOT send short updates like "SS2 dead". Always full format.**

---

## Breakoutprop Execution (app.breakoutprop.com)

### Opening Position
1. Click Ask price → dialog opens
2. Set lots via JS: `inp.value='X'; inp.dispatchEvent(new Event('input',{bubbles:true}))`
3. Click "Send Order"

### Closing Position  
1. Click X button on position row
2. Click "Close Position" confirm

### Speed Rules
- No intermediate screenshots — verify only at end
- Use JS evaluate for all interactions
- Be fast — markets move

---

## Strategy Evolution

### v1.0 (Original)
- 5 tiers, simple lot sizing
- Look-ahead bias (CLOSE prices)

### v2.0 (Fixed Backtest)
- 27 tiers, OPEN prices, realistic exits

### v3.0 (Kelly Optimized)
- 26 tiers, Kelly sizing, 3x scale

### v3.1 (Aggressive Scaling) ← CURRENT
- **12x scale for EVAL** (10x for funded)
- 228 trades, 91.7% WR
- Worst day $-1,802 ($1,198 buffer)
- Pass eval in ~20 trades avg

---

## ⚠️ EXECUTION RULES — MUST FOLLOW ⚠️

### Entry Timing
1. **Anchor triggers ≠ entry time** — anchor conditions can be met hours before entry
2. **Wait for SPECIFIED ENTRY HOUR** — check tier table for exact entry time
3. **Execute at candle OPEN** — when entry hour starts, not when conditions met

### Exit Conditions
1. **Check TRADED ASSET candles** — not anchor asset, not entry window reds
2. **Use candle color display** — signal-check.py shows 📊 HOURLY CANDLES
3. **2 consecutive greens** → exit at OPEN of candle AFTER 2nd green confirms
4. **Time cap** → exit at OPEN of candle AFTER cap expires

### Setup Viability
1. **Check if setups are still possible** — greens in window can kill setups
2. **Count reds vs window size** — if max possible reds < threshold, setup is DEAD
3. **Don't trust "1 red away"** — verify window hasn't been exhausted by greens

### Candle Color Verification
1. **Never infer from entry window counts** — those track different things
2. **Always check the 📊 HOURLY CANDLES output** — shows actual colors
3. **When in doubt, verify** — don't assume, check the data

---

## Live Trade Log

### 2026-03-06: EE3 ETH (First Live Trade)
- **Signal:** ETH 8am anchor, 2.1% range, 3/3 reds
- **Entry:** 1pm @ $1,970.58 (50 lots)
- **Exit:** 3pm @ ~$1,985 (2 greens: 1pm🟢, 2pm🟢)
- **P&L:** +$1,053 (actual platform)
- **Result:** ✅ WIN
- **Mistakes:** Entered 2h early at 11am, had to add 2nd position at proper 1pm entry
- **Account:** $100,000 → $101,041

---

## Lessons Learned

### 2026-03-06: First Live Execution
1. **Read entry time from tier table** — "Entry: ETH @ 1pm" means EXECUTE at 1pm
2. **Entry window reds ≠ exit candle colors** — completely different data
3. **Check candle colors explicitly** — added 📊 display to signal-check.py
4. **Verify setup viability** — greens in window can make setups impossible
5. **Follow strategy exactly** — deviations compound into errors

### 2026-03-02: Strategy Deep Dive
1. **Look-ahead bias is sneaky** — always use OPEN for entry
2. **Survivorship bias in tier selection** — tiers were picked for high WR
3. **Small samples mislead** — 100% on 6 trades ≠ 100% true WR
4. **2026 running at 83%** — expect 80-85% forward, not 91%
5. **Buffer matters** — 12x gives $1,198 buffer vs bust at 14x

---

*Last updated: 2026-03-06 3:36pm EST*
