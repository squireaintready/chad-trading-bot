# Red Candle Mean Reversion Strategy

**Version:** 3.3 (25-Tier, Risk-Adjusted Kelly, 12x EVAL Scale)  
**Last Updated:** 2026-03-08  
**Data Range:** January 2022 - February 2026 (4.17 years)

---

## Strategy Overview

Buy crypto after sustained selling pressure (consecutive red hourly candles), exit on bounce confirmation or time cap.

### Core Thesis
When an asset drops significantly over consecutive hours, it tends to bounce. We capture this mean reversion with high precision by:
1. Waiting for a large anchor candle to confirm the selloff
2. Counting red candles to confirm sustained pressure
3. Entering at a specific hour (at OPEN price)
4. Exiting when 2 consecutive green candles confirm bounce (at NEXT candle OPEN)
5. Or exiting at time cap if no bounce (at NEXT candle OPEN)

### Why It Works
- Large red candles = capitulation/forced selling
- Consecutive reds = exhausted sellers
- Specific anchor hours capture institutional trading patterns
- Cross-asset signals (ETH anchor → BTC trade) capture correlation dynamics

---

## Tier Naming Convention

**Format:** `[Anchor][Trade][#]`
- First char: Anchor asset (B=BTC, E=ETH, S=SOL)
- Second char: Trade asset (B=BTC, E=ETH, S=SOL)
- Number: tier variant

Example: `BS3` = BTC anchor → SOL trade, variant 3

---

## Execution Model (FULLY REALISTIC)

### Entry
- **Trigger Check:** All candles in the "window" must be CLOSED before entry
- **Entry Price:** OPEN of the entry hour candle
- **Rationale:** You place a market order when the entry candle starts

### Exit — 2 Green Candles
- **Signal:** Two consecutive hourly candles close GREEN
- **Exit Price:** OPEN of the candle AFTER the 2nd green
- **Rationale:** You don't know the 2nd candle is green until it closes, then you execute

### Exit — Time Cap
- **Signal:** Time cap expires (e.g., 4 hours after entry)
- **Exit Price:** OPEN of the candle AFTER the cap
- **Rationale:** Same logic — you know cap hit when candle closes, execute next open

### Timing Constraint
- **Rule:** Entry hour must be ≥ anchor hour + window
- **Why:** Ensures all red candles in window are CLOSED before entry decision

---

## Backtest Performance (12x EVAL Scale)

| Metric | Value |
|--------|-------|
| Tiers | 25 (EE6 removed) |
| Total Trades | 222 |
| Win Rate | **92.3%** (205W / 17L) |
| Total P&L | **$343,764** |
| Avg P&L/Trade | **$1,548** |
| Best Trade | $+16,664 |
| Worst Trade | $-1,802 |
| Worst Daily Loss | $-1,802 |
| Buffer to $3K Bust | $1,198 |
| Trades/Month | ~4.4 |

### Forward Expectations
- Backtest WR: 92.3%
- 2026 YTD WR: 83.3% (12 trades, 2 losses)
- Expected Forward WR: **80-85%**
- Reasons: Survivorship bias, small samples, 2023 luck

### Annual Performance
| Year | Trades | Win Rate | P&L | Avg |
|------|--------|----------|-----|-----|
| 2022 | 89 | 89% | $+171,049 | $+1,922 |
| 2023 | 31 | 100% | $+38,944 | $+1,256 |
| 2024 | 53 | 92% | $+63,095 | $+1,191 |
| 2025 | 37 | 97% | $+51,122 | $+1,382 |
| 2026 | 12 | 83% | $+19,553 | $+1,629 |

---

## Scale Modes

| Mode | Base | Scale | Worst Day | Buffer | Use When |
|------|------|-------|-----------|--------|----------|
| **EVAL** | $264,000 | **12x** | $-1,802 | $1,198 | Passing prop eval |
| FUNDED | $220,000 | 10x | $-1,500 | $1,500 | After passing |

---

## Position Sizing (12x EVAL Scale)

**Base Position:** $264,000  
**Method:** Half-Kelly Criterion

| Kelly | Position | BTC Lots | ETH Lots | SOL Lots | Actual Worst |
|-------|----------|----------|----------|----------|--------------|
| 0.50 | $132,000 | 1.47 | 52.8 | 880 | No loss ✅ |
| 0.44 | $116,160 | 1.29 | 46.5 | 774 | $-632 |
| 0.43 | $113,520 | 1.26 | 45.4 | 757 | $-1,601 |
| 0.41 | $108,240 | 1.20 | 43.3 | 722 | $-891 |
| 0.39 | $102,960 | 1.14 | 41.2 | 686 | $-1,493 |
| 0.30 | $79,200 | 0.88 | 31.7 | 528 | $-323 |
| 0.26 | $68,640 | 0.76 | 27.5 | 458 | $-1,501 |
| 0.20 | $52,800 | 0.59 | 21.1 | 352 | $-961 |
| 0.16 | $42,240 | 0.47 | 16.9 | 282 | $-1,802 |

**Note:** Kelly 0.50 tiers have 100% historical WR — never lost.

---

## 25-Tier Definitions

### BTC-Anchored (9 tiers)
| Tier | Anchor | Thresh | Reds | Trade | Entry | Cap | Kelly | WR |
|------|--------|--------|------|-------|-------|-----|-------|-----|
| BB1 | BTC 9am | >2.0% | 5+/6h | BTC | 3pm | 5h | 0.50 | 100% |
| BB2 | BTC 11am | >3.0% | 2+/3h | BTC | 6pm | 5h | 0.50 | 100% |
| BB3 | BTC 8am | >2.0% | 4+/5h | BTC | 3pm | 8h | 0.42 | 88% |
| BE1 | BTC 11am | >3.0% | 2+/3h | ETH | 6pm | 4h | 0.50 | 100% |
| BE2 | BTC 8am | >2.0% | 4+/5h | ETH | 3pm | 10h | 0.45 | 91% |
| BE3 | BTC 9am | >2.0% | 5+/6h | ETH | 3pm | 5h | 0.44 | 89% |
| BS1 | BTC 9am | >2.0% | 5+/6h | SOL | 5pm | 4h | 0.44 | 89% |
| BS2 | BTC 11am | >3.0% | 2+/3h | SOL | 6pm | 7h | 0.43 | 88% |
| BS3 | BTC 8am | >1.5% | 3+/3h | SOL | 3pm | 8h | 0.16 | 78% |

### ETH-Anchored (11 tiers)
| Tier | Anchor | Thresh | Reds | Trade | Entry | Cap | Kelly | WR |
|------|--------|--------|------|-------|-------|-----|-------|-----|
| EB1 | ETH 9am | >2.5% | 5+/6h | BTC | 4pm | 4h | 0.50 | 100% |
| EB2 | ETH 1pm | >4.0% | 2+/3h | BTC | 9pm | 3h | 0.41 | 86% |
| EE1 | ETH 9am | >3.0% | 5+/7h | ETH | 4pm | 4h | 0.50 | 100% |
| EE2 | ETH 1pm | >2.5% | 3+/3h | ETH | 4pm | 6h | 0.44 | 89% |
| EE3 | ETH 8am | >2.0% | 3+/3h | ETH | 1pm | 8h | 0.50 | 100% |
| EE4 | ETH 11am | >1.5% | 5+/5h | ETH | 5pm | 4h | 0.30 | 80% |
| EE5 | ETH 10am | >1.0% | 6+/6h | ETH | 5pm | 5h | 0.16 | 75% |
| ES1 | ETH 9am | >3.5% | 3+/4h | SOL | 4pm | 3h | 0.50 | 100% |
| ES2 | ETH 11am | >1.5% | 5+/5h | SOL | 6pm | 7h | 0.43 | 88% |
| ES3 | ETH 10am | >1.0% | 6+/6h | SOL | 4pm | 10h | 0.50 | 100% |
| ES4 | ETH 8am | >2.5% | 4+/5h | SOL | 3pm | 8h | 0.26 | 79% |

### SOL-Anchored (5 tiers)
| Tier | Anchor | Thresh | Reds | Trade | Entry | Cap | Kelly | WR |
|------|--------|--------|------|-------|-------|-----|-------|-----|
| SB1 | SOL 3pm | >4.0% | 2+/3h | BTC | 6pm | 7h | 0.39 | 86% |
| SB2 | SOL 12pm | >3.0% | 3+/3h | BTC | 5pm | 4h | 0.16 | 75% |
| SE1 | SOL 1pm | >2.5% | 3+/3h | ETH | 4pm | 6h | 0.41 | 86% |
| SS1 | SOL 11am | >1.5% | 6+/6h | SOL | 7pm | 3h | 0.50 | 100% |
| SS2 | SOL 5pm | >3.0% | 3+/4h | SOL | 11pm | 10h | 0.50 | 100% |

### Excluded
- **EE6:** 66.7% WR too low — removed

### Risk-Adjusted
- **BS3:** Kelly 0.32 → 0.16 (78% WR)
- **EE4:** Kelly 0.37 → 0.30 (80% WR)
- **EE5:** Kelly 0.20 → 0.16 (75% WR)
- **ES4:** Kelly 0.29 → 0.26 (79% WR)

---

## Risk Controls

| Control | Value | Purpose |
|---------|-------|---------|
| Daily Exposure Cap | $2,500 | Prevents exceeding worst day |
| Priority Cascade | First tier claims asset | No duplicate exposure |
| Stop Losses | None | Strategy tested without stops |
| Daily Realized Cap | $1,500 | Skip new entries after losses |

---

## Prop Account

| Setting | Value |
|---------|-------|
| Platform | breakoutprop.com |
| Account # | 673129 |
| Type | Classic eval, 1 Step |
| Size | $100,000 margin |
| Goal | +$10,000 (10%) |
| Max DD | -$6,000 (6%) |
| Daily Bust | -$3,000 |
| Our Worst Day | -$1,802 |
| Buffer | $1,198 ✅ |
| BTC/ETH Leverage | 5x |
| SOL Leverage | 2x |
| Daily Reset | 8pm EST |

---

## Commands

| Command | What It Does |
|---------|--------------|
| `/sta` | Quick: building tiers + open positions + P&L |
| `/sum` | Full day: all tiers by anchor hour + candle grid |

*(Avoid `/status` and `/summary` — clash with OpenClaw built-ins)*
| *(auto via cron)* | Alerts on anchors + signals + exits |

**Script modes:**
```bash
python3 tools/signal-check.py           # Auto mode (cron)
python3 tools/signal-check.py --status  # Quick status
python3 tools/signal-check.py --summary # Full day summary
```

**Anchor Hours:** 8am, 9am, 10am, 11am, 12pm, 1pm, 3pm, 5pm  
**Entry Hours:** 1pm, 3pm, 4pm, 5pm, 6pm, 7pm, 9pm, 11pm

**Auto Mode Behavior:**
- At anchor hours: Alert when new anchors form
- At entry hours: Alert when signals fire → EXECUTE
- Always: Monitor positions for exits
- Between hours: HEARTBEAT_OK (no noise)

---

## Signal Schedule

**Cron:** Hourly at :01, 9am-11pm EST (checks previous hour's anchor)

### Anchor Hours
| Hour | Tiers |
|------|-------|
| 8am | BE2, EE3, BB3, ES4, BS3 |
| 9am | BB1, EB1, EE1, ES1, BS1, BE3 |
| 10am | EE5, ES3 |
| 11am | BB2, BE1, SS1, ES2, EE4, BS2 |
| 12pm | SB2 |
| 1pm | EE2, SE1, EB2 |
| 3pm | SB1 |
| 5pm | SS2 |

### Entry Hours
| Hour | Tiers |
|------|-------|
| 1pm | EE3 |
| 3pm | BB1, BE2, BE3, BB3, ES4, BS3 |
| 4pm | EB1, EE1, ES1, EE2, SE1, ES3 |
| 5pm | BS1, EE4, EE5, SB2 |
| 6pm | BB2, BE1, ES2, BS2, SB1 |
| 7pm | SS1 |
| 9pm | EB2 |
| 11pm | SS2 |

---

## Files

| File | Purpose |
|------|---------|
| tools/signal-check.py | Live signal checker |
| tools/eval.py | Backtest simulator |
| tools/.bot-state.json | Current state |
| MEMORY.md | Long-term memory |
| PROP_ACCOUNT.md | Immutable prop rules |

---

*Strategy verified 2026-03-08. 2-char tier labels standardized.*
