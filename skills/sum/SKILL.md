---
name: sum
description: Trading summary - full day breakdown by anchor hour
user-invocable: true
---

# /sum - Trading Summary

Run the signal checker in summary mode to show:
- Current candle grid (last 8 hours)
- All 25 tiers grouped by anchor hour
- Status of each tier (no anchor, dead, building, triggered)

Execute this command:
```bash
python3 /Users/samjo/Desktop/autotrade/tools/signal-check.py --summary
```

Report the output to the user.
