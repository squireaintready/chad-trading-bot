---
name: sta
description: Trading status - building tiers + open positions + P&L
user-invocable: true
---

# /sta - Trading Status

Run the signal checker in status mode to show:
- Current candle grid (last 8 hours)
- Building tiers (anchors that formed, waiting for reds)
- Open positions with live P&L

Execute this command:
```bash
python3 /Users/samjo/Desktop/autotrade/tools/signal-check.py --status
```

Report the output to the user.
