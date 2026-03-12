#!/usr/bin/env python3
"""
25-Tier Signal Checker v4.0 — Clean Reporting System

Modes:
  (default)   Auto mode: anchors at anchor hours, signals at entry hours, always monitor
  --status    Quick: building tiers + open positions + P&L  
  --summary   Full day: all tiers by anchor hour + candle grid

Anchor Hours: 8am, 9am, 10am, 11am, 12pm, 1pm, 3pm, 5pm
Entry Hours:  1pm, 3pm, 4pm, 5pm, 6pm, 7pm, 9pm, 11pm

Strategy unchanged: 25 tiers, Risk-Adjusted Kelly, 12x EVAL scale
"""

import json
import sys
import argparse
import urllib.request
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_FILE = Path(__file__).parent / '.bot-state.json'

# ══════════════════════════════════════════════════════════════════════════════
# TIER DEFINITIONS (Strategy unchanged)
# ══════════════════════════════════════════════════════════════════════════════
TIERS = [
    # BTC anchor → BTC trade (BB)
    {'name':'BB1','anchor_asset':'BTC','anchor':9,'min_rng':2.0,'rt':5,'win':6,'entries':[('BTC',15,5)]},
    {'name':'BB2','anchor_asset':'BTC','anchor':11,'min_rng':3.0,'rt':2,'win':3,'entries':[('BTC',18,5)]},
    {'name':'BB3','anchor_asset':'BTC','anchor':8,'min_rng':2.0,'rt':4,'win':5,'entries':[('BTC',15,8)]},
    # BTC anchor → ETH trade (BE)
    {'name':'BE1','anchor_asset':'BTC','anchor':11,'min_rng':3.0,'rt':2,'win':3,'entries':[('ETH',18,4)]},
    {'name':'BE2','anchor_asset':'BTC','anchor':8,'min_rng':2.0,'rt':4,'win':5,'entries':[('ETH',15,10)]},
    {'name':'BE3','anchor_asset':'BTC','anchor':9,'min_rng':2.0,'rt':5,'win':6,'entries':[('ETH',15,5)]},
    # BTC anchor → SOL trade (BS)
    {'name':'BS1','anchor_asset':'BTC','anchor':9,'min_rng':2.0,'rt':5,'win':6,'entries':[('SOL',17,4)]},
    {'name':'BS2','anchor_asset':'BTC','anchor':11,'min_rng':3.0,'rt':2,'win':3,'entries':[('SOL',18,7)]},
    {'name':'BS3','anchor_asset':'BTC','anchor':8,'min_rng':1.5,'rt':3,'win':3,'entries':[('SOL',15,8)]},
    # ETH anchor → BTC trade (EB)
    {'name':'EB1','anchor_asset':'ETH','anchor':9,'min_rng':2.5,'rt':5,'win':6,'entries':[('BTC',16,4)]},
    {'name':'EB2','anchor_asset':'ETH','anchor':13,'min_rng':4.0,'rt':2,'win':3,'entries':[('BTC',21,3)]},
    # ETH anchor → ETH trade (EE)
    {'name':'EE1','anchor_asset':'ETH','anchor':9,'min_rng':3.0,'rt':5,'win':7,'entries':[('ETH',16,4)]},
    {'name':'EE2','anchor_asset':'ETH','anchor':13,'min_rng':2.5,'rt':3,'win':3,'entries':[('ETH',16,6)]},
    {'name':'EE3','anchor_asset':'ETH','anchor':8,'min_rng':2.0,'rt':3,'win':3,'entries':[('ETH',13,8)]},
    {'name':'EE4','anchor_asset':'ETH','anchor':11,'min_rng':1.5,'rt':5,'win':5,'entries':[('ETH',17,4)]},
    {'name':'EE5','anchor_asset':'ETH','anchor':10,'min_rng':1.0,'rt':6,'win':6,'entries':[('ETH',17,5)]},
    # ETH anchor → SOL trade (ES)
    {'name':'ES1','anchor_asset':'ETH','anchor':9,'min_rng':3.5,'rt':3,'win':4,'entries':[('SOL',16,3)]},
    {'name':'ES2','anchor_asset':'ETH','anchor':11,'min_rng':1.5,'rt':5,'win':5,'entries':[('SOL',18,7)]},
    {'name':'ES3','anchor_asset':'ETH','anchor':10,'min_rng':1.0,'rt':6,'win':6,'entries':[('SOL',16,10)]},
    {'name':'ES4','anchor_asset':'ETH','anchor':8,'min_rng':2.5,'rt':4,'win':5,'entries':[('SOL',15,8)]},
    # SOL anchor → BTC trade (SB)
    {'name':'SB1','anchor_asset':'SOL','anchor':15,'min_rng':4.0,'rt':2,'win':3,'entries':[('BTC',18,7)]},
    {'name':'SB2','anchor_asset':'SOL','anchor':12,'min_rng':3.0,'rt':3,'win':3,'entries':[('BTC',17,4)]},
    # SOL anchor → ETH trade (SE)
    {'name':'SE1','anchor_asset':'SOL','anchor':13,'min_rng':2.5,'rt':3,'win':3,'entries':[('ETH',16,6)]},
    # SOL anchor → SOL trade (SS)
    {'name':'SS1','anchor_asset':'SOL','anchor':11,'min_rng':1.5,'rt':6,'win':6,'entries':[('SOL',19,3)]},
    {'name':'SS2','anchor_asset':'SOL','anchor':17,'min_rng':3.0,'rt':3,'win':4,'entries':[('SOL',23,10)]},
]

# Kelly multipliers (risk-adjusted)
KELLY = {
    'BB1': 0.50, 'BB2': 0.50, 'BB3': 0.42,
    'BE1': 0.50, 'BE2': 0.45, 'BE3': 0.44,
    'BS1': 0.44, 'BS2': 0.43, 'BS3': 0.16,
    'EB1': 0.50, 'EB2': 0.41,
    'EE1': 0.50, 'EE2': 0.44, 'EE3': 0.50, 'EE4': 0.30, 'EE5': 0.16,
    'ES1': 0.50, 'ES2': 0.43, 'ES3': 0.50, 'ES4': 0.26,
    'SB1': 0.39, 'SB2': 0.16,
    'SE1': 0.41,
    'SS1': 0.50, 'SS2': 0.50,
}

BASE_POSITION = 264000  # 12x EVAL scale

# Win rates from backtest
WIN_RATE = {
    'BB1': 100, 'BB2': 100, 'BB3': 88,
    'BE1': 100, 'BE2': 91, 'BE3': 89,
    'BS1': 89, 'BS2': 88, 'BS3': 78,
    'EB1': 100, 'EB2': 86,
    'EE1': 100, 'EE2': 89, 'EE3': 100, 'EE4': 80, 'EE5': 75,
    'ES1': 100, 'ES2': 88, 'ES3': 100, 'ES4': 79,
    'SB1': 86, 'SB2': 75,
    'SE1': 86,
    'SS1': 100, 'SS2': 100,
}

def get_lots(tier_name, asset, price=None):
    """Get lot size for a tier. Uses live price if provided, else estimates."""
    kelly = KELLY.get(tier_name, 0)
    position = BASE_POSITION * kelly
    if price and price > 0:
        return position / price
    # Fallback estimates
    est = {'BTC': 90000, 'ETH': 2500, 'SOL': 150}
    return position / est.get(asset, 1)

def fmt_lots(lots, asset):
    """Format lot count for display."""
    if asset == 'BTC':
        return f"{lots:.2f}"
    elif asset == 'ETH':
        return f"{lots:.1f}"
    else:
        return f"{lots:.0f}"

# Hour classifications
ANCHOR_HOURS = {8, 9, 10, 11, 12, 13, 15, 17}
ENTRY_HOURS = {13, 15, 16, 17, 18, 19, 21, 23}

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_est_now():
    utc_now = datetime.now(timezone.utc)
    y = utc_now.year
    mar1 = datetime(y, 3, 1, tzinfo=timezone.utc)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7, hours=7)
    nov1 = datetime(y, 11, 1, tzinfo=timezone.utc)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7, hours=6)
    off = -4 if dst_start <= utc_now < dst_end else -5
    return utc_now + timedelta(hours=off), off

def fmt_hour(h):
    if h == 0: return "12am"
    elif h == 12: return "12pm"
    elif h < 12: return f"{h}am"
    else: return f"{h-12}pm"

def fmt_hour_short(h):
    if h == 0: return "12a"
    elif h == 12: return "12p"
    elif h < 12: return f"{h}a"
    else: return f"{h-12}p"

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'trade_count': 0, 'positions': [], 'signals_fired_today': [], 
            'anchors_alerted_today': [], 'daily_realized_pnl': 0.0, 'last_date': ''}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def fetch_price(symbol):
    url = f"https://min-api.cryptocompare.com/data/price?fsym={symbol}&tsyms=USD"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return float(json.loads(resp.read()).get('USD', 0))
    except:
        return 0

def fetch_candles(symbol, limit=48):
    for exchange in ['coinbase', '']:
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={symbol}&tsym=USD&limit={limit}"
        if exchange:
            url += f"&e={exchange}"
        try:
            time.sleep(0.1)
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            if data.get('Response') == 'Success':
                candles = data['Data']['Data']
                if candles:
                    return candles
        except:
            pass
    return []

def get_candle_cache(now, utc_off):
    """Fetch and process candles for all assets."""
    today = now.strftime('%Y-%m-%d')
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    cache = {}
    
    for sym in ['BTC', 'ETH', 'SOL']:
        raw = fetch_candles(sym, 48)
        if not raw:
            continue
        candles = {}
        for c in raw:
            ts = datetime.fromtimestamp(c['time'], tz=timezone.utc) + timedelta(hours=utc_off)
            cdate = ts.strftime('%Y-%m-%d')
            if cdate in (today, yesterday):
                o, cl = float(c['open']), float(c['close'])
                h, l = float(c['high']), float(c['low'])
                candles[ts.hour] = {
                    'open': o, 'close': cl, 'high': h, 'low': l,
                    'red': cl < o, 'green': cl >= o,
                    'range_pct': (h - l) / o * 100 if o > 0 else 0,
                    'date': cdate
                }
        cache[sym] = candles
    return cache

# ══════════════════════════════════════════════════════════════════════════════
# TIER ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
def analyze_tier(tier, candle_cache, now, today):
    """Analyze a single tier's status."""
    anchor_asset = tier['anchor_asset']
    anchor_h = tier['anchor']
    candles = candle_cache.get(anchor_asset, {})
    
    # Get entry info
    trade_asset, entry_h, time_cap = tier['entries'][0]
    kelly = KELLY.get(tier['name'], 0)
    position = BASE_POSITION * kelly
    
    result = {
        'tier': tier['name'],
        'anchor_asset': anchor_asset,
        'anchor_hour': anchor_h,
        'trade_asset': trade_asset,
        'entry_hour': entry_h,
        'time_cap': time_cap,
        'kelly': kelly,
        'position': position,
        'thresh': tier['min_rng'],
        'reds_needed': tier['rt'],
        'window': tier['win'],
        'status': 'pending',  # pending, no_anchor, dead, building, triggered
        'reason': '',
    }
    
    # Check if anchor hour has passed
    if now.hour <= anchor_h:
        result['status'] = 'pending'
        result['reason'] = f'Anchor at {fmt_hour(anchor_h)} not yet'
        return result
    
    # Check if anchor candle exists for today
    if anchor_h not in candles or candles[anchor_h].get('date') != today:
        result['status'] = 'no_data'
        result['reason'] = 'No candle data'
        return result
    
    anchor = candles[anchor_h]
    
    # Check if anchor was red
    if not anchor['red']:
        result['status'] = 'no_anchor'
        result['reason'] = f'{fmt_hour(anchor_h)} was GREEN'
        return result
    
    # Check threshold
    result['range_pct'] = anchor['range_pct']
    if anchor['range_pct'] < tier['min_rng']:
        result['status'] = 'no_anchor'
        result['reason'] = f'{anchor["range_pct"]:.1f}% < {tier["min_rng"]}% threshold'
        return result
    
    # Anchor formed! Count reds and greens in CLOSED candles only
    # Current hour's candle is still open — exclude it
    reds = 0
    greens_in_closed = 0
    for off in range(tier['win']):
        h = anchor_h + off
        if h >= now.hour:
            continue  # Candle not closed yet — skip
        if h in candles and candles[h].get('date') == today:
            if candles[h]['red']:
                reds += 1
            else:
                greens_in_closed += 1

    result['reds'] = reds
    result['reds_needed'] = tier['rt']

    # Max possible reds = current reds + remaining unclosed hours
    window_end = anchor_h + tier['win']
    remaining_hours = max(0, window_end - now.hour)
    max_possible_reds = reds + remaining_hours

    if reds >= tier['rt']:
        result['status'] = 'triggered'
        result['reason'] = f'{reds}/{tier["rt"]} reds ✓'
    elif max_possible_reds < tier['rt']:
        # Too many greens — impossible to reach threshold
        result['status'] = 'dead'
        result['reason'] = f'{reds}/{tier["rt"]} reds, {greens_in_closed} greens killed it'
    else:
        if now.hour < window_end:
            result['status'] = 'building'
            result['reason'] = f'{reds}/{tier["rt"]} reds, waiting'
        else:
            result['status'] = 'dead'
            result['reason'] = f'Only {reds}/{tier["rt"]} reds in window'
    
    return result

def analyze_all_tiers(candle_cache, now, today):
    """Analyze all tiers and group by status."""
    results = {'pending': [], 'no_anchor': [], 'dead': [], 'building': [], 'triggered': [], 'no_data': []}
    
    for tier in TIERS:
        analysis = analyze_tier(tier, candle_cache, now, today)
        results[analysis['status']].append(analysis)
    
    return results

# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def print_candle_grid(candle_cache, now):
    """Print candle grid from 8am to current hour, Discord-aligned."""
    # Show 8am through current hour (trading hours only)
    start_h = 8
    end_h = min(now.hour, 23)
    if end_h < start_h:
        return
    hours = list(range(start_h, end_h + 1))

    # Discord: emojis render ~2.2 monospace chars wide
    # Use "  X" per cell (2 spaces + emoji ≈ 4.2 visual chars)
    # Match headers at 4 chars per column
    header = ""
    for h in hours:
        lbl = fmt_hour_short(h)
        header += lbl.rjust(4)
    print(f"    {header}")

    for asset in ['BTC', 'ETH', 'SOL']:
        candles = candle_cache.get(asset, {})
        row = ""
        for h in hours:
            if h in candles:
                dot = "🔴" if candles[h]['red'] else "🟢"
            else:
                dot = "⬜"
            row += "  " + dot
        print(f"{asset}{row}")
    print()

def print_status(candle_cache, now, today):
    """Quick status: building + positions + P&L."""
    state = load_state()
    analysis = analyze_all_tiers(candle_cache, now, today)
    
    print(f"📊 Status @ {now.strftime('%I:%M%p').lstrip('0')} — {now.strftime('%a %b %d')}")
    print()
    
    # Candle grid
    print_candle_grid(candle_cache, now)
    
    # Building tiers
    building = analysis['building']
    triggered = analysis['triggered']
    
    if triggered:
        print("🎯 TRIGGERED:")
        for t in triggered:
            ta, tn = t['trade_asset'], t['tier']
            lots_str = fmt_lots(get_lots(tn, ta), ta)
            wr = WIN_RATE.get(tn, 0)
            print(f"  {tn}: → {ta} @ {fmt_hour(t['entry_hour'])} | {lots_str} lots | k{t['kelly']:.2f} | {wr}%")
        print()

    if building:
        print("⏳ BUILDING:")
        for t in building:
            ta, tn = t['trade_asset'], t['tier']
            lots_str = fmt_lots(get_lots(tn, ta), ta)
            wr = WIN_RATE.get(tn, 0)
            print(f"  {tn}: {t['reds']}/{t['reds_needed']} reds → {ta} @ {fmt_hour(t['entry_hour'])} | {lots_str} lots | k{t['kelly']:.2f} | {wr}%")
        print()
    
    if not building and not triggered:
        print("⏳ BUILDING: None")
        print()
    
    # Open positions
    positions = state.get('positions', [])
    if positions:
        print(f"📈 POSITIONS ({len(positions)}):")
        for p in positions:
            price = fetch_price(p['asset'])
            pnl_pct = (price - p['entry_price']) / p['entry_price'] * 100 if p['entry_price'] > 0 else 0
            pnl_dollar = p['position'] * (pnl_pct / 100)
            emoji = '📈' if pnl_dollar >= 0 else '📉'
            print(f"  {emoji} {p['tier']} {p['asset']} @ ${p['entry_price']:,.2f}")
            print(f"     Now: ${price:,.2f} | P&L: ${pnl_dollar:+,.0f} ({pnl_pct:+.1f}%)")
    else:
        print("📈 POSITIONS: None")
    print()
    
    # Daily P&L
    daily_pnl = state.get('daily_realized_pnl', 0)
    if daily_pnl != 0:
        print(f"💰 Daily P&L: ${daily_pnl:+,.0f}")

def print_summary(candle_cache, now, today):
    """Full day summary by anchor hour."""
    analysis = analyze_all_tiers(candle_cache, now, today)
    
    print(f"📋 Summary — {now.strftime('%a %b %d')}")
    print()
    
    # Candle grid
    print_candle_grid(candle_cache, now)
    
    # Group tiers by anchor hour
    by_hour = {}
    for status, tiers in analysis.items():
        for t in tiers:
            h = t['anchor_hour']
            if h not in by_hour:
                by_hour[h] = []
            by_hour[h].append(t)
    
    # Print by anchor hour
    printed_key = False
    for hour in sorted(ANCHOR_HOURS):
        if hour > now.hour:
            continue  # Skip future hours

        tiers_at_hour = by_hour.get(hour, [])
        if not tiers_at_hour:
            continue

        # Determine overall status for this hour
        statuses = [t['status'] for t in tiers_at_hour]
        has_active = any(s in ('triggered', 'building') for s in statuses)
        if 'triggered' in statuses:
            hour_emoji = "🎯"
        elif 'building' in statuses:
            hour_emoji = "⏳"
        elif all(s in ('no_anchor', 'dead', 'no_data') for s in statuses):
            hour_emoji = "❌"
        else:
            hour_emoji = "⚪"

        # Print key header once, before first section with active tiers
        if has_active and not printed_key:
            print("Tier  Reds  Trade    Lots   Kelly  WR")
            print("────  ────  ───────  ─────  ─────  ───")
            printed_key = True

        print(f"{hour_emoji} {fmt_hour(hour)} ANCHORS:")

        for t in tiers_at_hour:
            ta = t['trade_asset']
            tn = t['tier']
            wr = WIN_RATE.get(tn, 0)
            k = t['kelly']
            lots = get_lots(tn, ta)
            lots_str = fmt_lots(lots, ta)

            if t['status'] in ('triggered', 'building'):
                reds_str = f"{t.get('reds', 0)}/{t['reds_needed']}" if t['status'] == 'building' else "✅"
                entry_str = f"{ta}@{fmt_hour(t['entry_hour'])}"
                print(f"  {tn:<4}  {reds_str:<4}  {entry_str:<7}  {lots_str:>5}  {k:.2f}   {wr}%")
            else:
                reason = t.get('reason', 'No data')
                print(f"  ❌ {tn}: {reason}")
        print()
    
    # Future anchor hours
    future_hours = [h for h in sorted(ANCHOR_HOURS) if h > now.hour]
    if future_hours:
        print("⏸️ PENDING HOURS: " + ", ".join(fmt_hour(h) for h in future_hours))

# ══════════════════════════════════════════════════════════════════════════════
# AUTO MODE (Cron)
# ══════════════════════════════════════════════════════════════════════════════
def check_for_new_anchors(candle_cache, now, today, state):
    """Check for newly formed anchors and return alerts."""
    alerts = []
    analysis = analyze_all_tiers(candle_cache, now, today)
    
    # Get anchors we've already alerted on today
    alerted = set(state.get('anchors_alerted_today', []))
    
    for t in analysis['building'] + analysis['triggered']:
        tier_name = t['tier']
        if tier_name not in alerted:
            alerts.append(t)
            alerted.add(tier_name)
    
    state['anchors_alerted_today'] = list(alerted)
    return alerts

def check_for_signals(candle_cache, now, today, state):
    """Check for entry signals and return them."""
    analysis = analyze_all_tiers(candle_cache, now, today)
    signals = []
    
    # Already fired today
    fired = set(state.get('signals_fired_today', []))
    
    # Already holding
    held_assets = set(p['asset'] for p in state.get('positions', []))
    
    for t in analysis['triggered']:
        tier_name = t['tier']
        entry_hour = t['entry_hour']
        trade_asset = t['trade_asset']
        
        # Check if it's entry time
        if now.hour < entry_hour:
            continue
        
        # Check if already fired
        if tier_name in fired:
            continue
        
        # Check if asset already held (priority cascade)
        if trade_asset in held_assets:
            continue
        
        # Signal fires!
        price = fetch_price(trade_asset)
        if price <= 0:
            continue
        
        signals.append({
            **t,
            'price': price,
            'lots': t['position'] / price,
        })
        
        fired.add(tier_name)
        held_assets.add(trade_asset)
    
    state['signals_fired_today'] = list(fired)
    return signals

def monitor_positions(candle_cache, now, state):
    """Monitor open positions for exits."""
    positions = state.get('positions', [])
    if not positions:
        return []
    
    events = []
    remaining = []
    
    for pos in positions:
        asset = pos['asset']
        entry_hour = pos['entry_hour']
        time_cap = pos['time_cap']
        
        hours_held = now.hour - entry_hour
        if hours_held < 0:
            hours_held += 24
        
        current_price = fetch_price(asset)
        candles = candle_cache.get(asset, {})
        
        # Check exit conditions
        should_exit = False
        reason = None
        
        # Time cap
        if hours_held >= time_cap:
            should_exit = True
            reason = 'time_cap'
        
        # 2 green candles
        if not should_exit:
            prev_h = (now.hour - 1) % 24
            prev_prev_h = (now.hour - 2) % 24
            if prev_h in candles and prev_prev_h in candles:
                if candles[prev_h]['green'] and candles[prev_prev_h]['green']:
                    should_exit = True
                    reason = '2_green'
        
        entry_price = pos['entry_price']
        pnl_pct = (current_price - entry_price) / entry_price * 100 if entry_price > 0 else 0
        pnl_dollar = pos['position'] * (pnl_pct / 100)
        
        if should_exit:
            state['daily_realized_pnl'] = state.get('daily_realized_pnl', 0) + pnl_dollar
            events.append({
                'type': 'EXIT',
                'tier': pos['tier'],
                'asset': asset,
                'entry_price': entry_price,
                'exit_price': current_price,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'reason': reason,
            })
        else:
            events.append({
                'type': 'HOLDING',
                'tier': pos['tier'],
                'asset': asset,
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'hours_held': hours_held,
                'time_cap': time_cap,
            })
            remaining.append(pos)
    
    state['positions'] = remaining
    return events

def run_auto(candle_cache, now, today):
    """Auto mode: smart about anchor hours vs entry hours."""
    state = load_state()
    
    # Reset daily state
    if state.get('last_date') != today:
        state['signals_fired_today'] = []
        state['anchors_alerted_today'] = []
        state['daily_realized_pnl'] = 0.0
        state['last_date'] = today
    
    output = []
    
    # Check for new anchors (at anchor hours)
    anchor_alerts = check_for_new_anchors(candle_cache, now, today, state)
    if anchor_alerts:
        output.append("🔔 NEW ANCHORS FORMED:")
        for a in anchor_alerts:
            status = f"{a.get('reds', 0)}/{a['reds_needed']} reds" if a['status'] == 'building' else 'TRIGGERED ✓'
            output.append(f"   {a['tier']}: {a['anchor_asset']} {fmt_hour(a['anchor_hour'])} → {a['range_pct']:.1f}% | {status}")
            output.append(f"      → {a['trade_asset']} @ {fmt_hour(a['entry_hour'])} | ${a['position']:,.0f}")
        output.append("")
    
    # Check for entry signals (at entry hours)
    signals = check_for_signals(candle_cache, now, today, state)
    if signals:
        output.append("🚨 ENTRY SIGNALS:")
        for s in signals:
            output.append(f"   {s['tier']}: BUY {s['trade_asset']} @ ${s['price']:,.2f}")
            output.append(f"      Position: ${s['position']:,.0f} | Lots: {s['lots']:.2f}")
            output.append(f"      Time cap: {s['time_cap']}h | Kelly: {s['kelly']:.2f}")
            output.append("      ⚡ EXECUTE NOW")
            
            # Record position
            state.setdefault('positions', []).append({
                'tier': s['tier'],
                'asset': s['trade_asset'],
                'entry_price': s['price'],
                'position': s['position'],
                'entry_hour': s['entry_hour'],
                'time_cap': s['time_cap'],
                'entry_time': now.strftime('%Y-%m-%d %H:%M:%S EST'),
            })
        output.append("")
    
    # Monitor positions
    position_events = monitor_positions(candle_cache, now, state)
    exits = [e for e in position_events if e['type'] == 'EXIT']
    
    if exits:
        output.append("📤 EXIT SIGNALS:")
        for e in exits:
            emoji = '✅' if e['pnl_dollar'] >= 0 else '🔴'
            output.append(f"   {emoji} {e['tier']} {e['asset']}: {e['reason']}")
            output.append(f"      Entry ${e['entry_price']:,.2f} → Exit ${e['exit_price']:,.2f}")
            output.append(f"      P&L: ${e['pnl_dollar']:+,.0f} ({e['pnl_pct']:+.1f}%)")
            output.append("      ⚡ CLOSE NOW")
        output.append("")
    
    # Save state
    state['last_check'] = now.strftime('%Y-%m-%d %H:%M:%S EST')
    save_state(state)
    
    # Print output
    if output:
        for line in output:
            print(line)
    else:
        # Only print "no signals" if it's an anchor or entry hour
        if now.hour in ANCHOR_HOURS or now.hour in ENTRY_HOURS:
            print(f"📊 {now.strftime('%I:%M%p').lstrip('0')}: No new signals")
        else:
            print("HEARTBEAT_OK")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description='Signal Checker v4.0')
    parser.add_argument('--status', action='store_true', help='Quick status: building + positions')
    parser.add_argument('--summary', action='store_true', help='Full day summary by anchor hour')
    args = parser.parse_args()
    
    now, utc_off = get_est_now()
    today = now.strftime('%Y-%m-%d')
    candle_cache = get_candle_cache(now, utc_off)
    
    if args.status:
        print_status(candle_cache, now, today)
    elif args.summary:
        print_summary(candle_cache, now, today)
    else:
        run_auto(candle_cache, now, today)

if __name__ == "__main__":
    main()
