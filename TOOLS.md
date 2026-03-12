# TOOLS.md - Local Notes

## Breakoutprop Trading (app.breakoutprop.com)

### ⚠️ EXECUTION CHECKLIST — BEFORE EVERY TRADE ⚠️
1. **Verify entry hour** — check tier table, NOT when anchor triggers
2. **Check candle colors** — use 📊 HOURLY CANDLES from signal-check.py
3. **Verify setup is alive** — count greens in window, ensure reds are still possible
4. **Confirm lots** — check Kelly and position size for the specific tier
5. **Execute at candle OPEN** — when entry hour starts

### Opening a Position
1. Click Ask price button on watchlist row → dialog opens
2. Set lots: `input.value = 'X'; input.dispatchEvent(new Event('input', {bubbles:true})); input.dispatchEvent(new Event('change', {bubbles:true}));`
3. Order Type: Market (default)
4. Click "Send Order" button

### Closing a Position
1. Click X button on position row (last non-disabled button in row)
2. Click "Close Position" confirm button

### Exit Rules
- **2 consecutive greens on TRADED asset** → exit at OPEN of next candle
- **Time cap expires** → exit at OPEN of next candle
- Check 📊 HOURLY CANDLES for traded asset colors, NOT entry window reds

### Tips
- Don't take intermediate screenshots — only verify at end
- Use JS evaluate for speed
- One-click trading toggle is at top (usually OFF)

### Account
- Platform: breakoutprop.com
- Account: #673129
- Watchlist: "chad" with BTC, ETH, SOL

---

## Other Tools

### TTS
- Use `tts` tool for voice output

### Browser
- Profile: "openclaw" for isolated browser
- Use JS evaluate for complex interactions
