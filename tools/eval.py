#!/usr/bin/env python3
"""
Unified eval tool — 25-Tier System v3.3 with Risk-Adjusted Kelly Sizing
Usage:
  python3 tools/eval.py                    # Full eval sim (default)
  python3 tools/eval.py --mode combined    # Combined priority cascade
  python3 tools/eval.py --mode kelly       # Kelly-weighted returns
  python3 tools/eval.py --year 2025        # Start eval from specific year
  python3 tools/eval.py --verbose          # Show every trade

Removed: EE6 (66.7% WR too low)
Risk-adjusted Kelly: BS3 (0.16), EE4 (0.30), EE5 (0.16), ES4 (0.26)
"""

import json, sys, argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pathlib import Path

DATA_FILE = Path(__file__).parent / "mega-backtest-data-complete.json"

# ══════════════════════════════════════════════════════════════════════════════
# 25-TIER SYSTEM v3.3 — Risk-Adjusted Kelly
# ══════════════════════════════════════════════════════════════════════════════
# VERIFIED 2026-03-03: Fully realistic (OPEN entry, OPEN exit after confirmation)
# Naming: BB1 = BTC anchor → BTC trade (variant 1)
#         ES2 = ETH anchor → SOL trade (variant 2)
# REMOVED: EE6 (66.7% WR too low)
# RISK-ADJUSTED: BS3, EE4, EE5, ES4 (reduced Kelly for lower WR)
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
    {'name':'BS3','anchor_asset':'BTC','anchor':8,'min_rng':1.5,'rt':3,'win':3,'entries':[('SOL',15,8)]},  # RISK-ADJUSTED
    # ETH anchor → BTC trade (EB)
    {'name':'EB1','anchor_asset':'ETH','anchor':9,'min_rng':2.5,'rt':5,'win':6,'entries':[('BTC',16,4)]},
    {'name':'EB2','anchor_asset':'ETH','anchor':13,'min_rng':4.0,'rt':2,'win':3,'entries':[('BTC',21,3)]},
    # ETH anchor → ETH trade (EE)
    {'name':'EE1','anchor_asset':'ETH','anchor':9,'min_rng':3.0,'rt':5,'win':7,'entries':[('ETH',16,4)]},
    {'name':'EE2','anchor_asset':'ETH','anchor':13,'min_rng':2.5,'rt':3,'win':3,'entries':[('ETH',16,6)]},
    {'name':'EE3','anchor_asset':'ETH','anchor':8,'min_rng':2.0,'rt':3,'win':3,'entries':[('ETH',13,8)]},
    {'name':'EE4','anchor_asset':'ETH','anchor':11,'min_rng':1.5,'rt':5,'win':5,'entries':[('ETH',17,4)]},  # RISK-ADJUSTED
    {'name':'EE5','anchor_asset':'ETH','anchor':10,'min_rng':1.0,'rt':6,'win':6,'entries':[('ETH',17,5)]},  # RISK-ADJUSTED
    # EE6 REMOVED (66.7% WR)
    # ETH anchor → SOL trade (ES)
    {'name':'ES1','anchor_asset':'ETH','anchor':9,'min_rng':3.5,'rt':3,'win':4,'entries':[('SOL',16,3)]},
    {'name':'ES2','anchor_asset':'ETH','anchor':11,'min_rng':1.5,'rt':5,'win':5,'entries':[('SOL',18,7)]},
    {'name':'ES3','anchor_asset':'ETH','anchor':10,'min_rng':1.0,'rt':6,'win':6,'entries':[('SOL',16,10)]},
    {'name':'ES4','anchor_asset':'ETH','anchor':8,'min_rng':2.5,'rt':4,'win':5,'entries':[('SOL',15,8)]},  # RISK-ADJUSTED
    # SOL anchor → BTC trade (SB)
    {'name':'SB1','anchor_asset':'SOL','anchor':15,'min_rng':4.0,'rt':2,'win':3,'entries':[('BTC',18,7)]},
    {'name':'SB2','anchor_asset':'SOL','anchor':12,'min_rng':3.0,'rt':3,'win':3,'entries':[('BTC',17,4)]},
    # SOL anchor → ETH trade (SE)
    {'name':'SE1','anchor_asset':'SOL','anchor':13,'min_rng':2.5,'rt':3,'win':3,'entries':[('ETH',16,6)]},
    # SOL anchor → SOL trade (SS)
    {'name':'SS1','anchor_asset':'SOL','anchor':11,'min_rng':1.5,'rt':6,'win':6,'entries':[('SOL',19,3)]},
    {'name':'SS2','anchor_asset':'SOL','anchor':17,'min_rng':3.0,'rt':3,'win':4,'entries':[('SOL',23,10)]},
]

# ══════════════════════════════════════════════════════════════════════════════
# KELLY-BASED POSITION SIZING
# ══════════════════════════════════════════════════════════════════════════════
# Half-Kelly for safety margin
# Kelly = (p * b - q) / b where p=WR, q=1-p, b=avg_win/avg_loss
BASE_POSITION = 264000  # 12x scale for EVAL MODE (10x=$220K for funded)

KELLY_MULTIPLIERS = {
    # BTC anchor
    'BB1': 0.50, 'BB2': 0.50, 'BB3': 0.42,
    'BE1': 0.50, 'BE2': 0.45, 'BE3': 0.44,
    'BS1': 0.44, 'BS2': 0.43, 'BS3': 0.16,  # RISK-ADJUSTED (was 0.32)
    # ETH anchor
    'EB1': 0.50, 'EB2': 0.41,
    'EE1': 0.50, 'EE2': 0.44, 'EE3': 0.50, 'EE4': 0.30, 'EE5': 0.16,  # EE4/EE5 RISK-ADJUSTED
    'ES1': 0.50, 'ES2': 0.43, 'ES3': 0.50, 'ES4': 0.26,  # ES4 RISK-ADJUSTED (was 0.29)
    # SOL anchor
    'SB1': 0.39, 'SB2': 0.16,
    'SE1': 0.41,
    'SS1': 0.50, 'SS2': 0.50,
}

AVG_PRICES = {'BTC': 90000, 'ETH': 2500, 'SOL': 150}

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
_cache = {}

def is_dst(dt_utc):
    y = dt_utc.year
    mar1 = datetime(y,3,1,tzinfo=timezone.utc)
    ms = mar1 + timedelta(days=(6-mar1.weekday())%7)
    ds = ms + timedelta(days=7, hours=7)
    nov1 = datetime(y,11,1,tzinfo=timezone.utc)
    ns = nov1 + timedelta(days=(6-nov1.weekday())%7)
    de = ns + timedelta(hours=6)
    return ds <= dt_utc < de

def to_est(dt_utc):
    off = -4 if is_dst(dt_utc) else -5
    e = dt_utc + timedelta(hours=off)
    return e.hour, e.weekday(), e.date()

def load_data():
    if 'assets' in _cache:
        return _cache['assets'], _cache['day_maps'], _cache['dates']
    
    with open(DATA_FILE) as f:
        raw = json.load(f)
    
    assets = {}; day_maps = {}
    for name in ['BTC','ETH','SOL']:
        if name not in raw: continue
        seen = set(); data = []
        for d in raw[name]:
            if d[0] in seen: continue
            seen.add(d[0])
            ts = datetime.fromtimestamp(d[0]/1000, tz=timezone.utc)
            eh, edow, edate = to_est(ts)
            data.append({'ts':ts,'o':d[1],'h':d[2],'l':d[3],'c':d[4],
                'hour':eh,'dow':edow,'date':edate,
                'red':d[4]<d[1],'green':d[4]>d[1],
                'range_pct':(d[2]-d[3])/d[1]*100 if d[1]>0 else 0})
        data.sort(key=lambda x: x['ts'])
        assets[name] = data
        dm = defaultdict(dict)
        for i, d in enumerate(data):
            dm[d['date']][d['hour']] = (i, d)
        day_maps[name] = dm
    
    dates = sorted(set(d['date'] for d in assets['BTC']))
    _cache.update(assets=assets, day_maps=day_maps, dates=dates)
    return assets, day_maps, dates

# ══════════════════════════════════════════════════════════════════════════════
# CORE SIMULATION
# ══════════════════════════════════════════════════════════════════════════════
def sim_2g(data, ei, ep, tc):
    """Simulate trade with 2-green exit or time cap."""
    mx = len(data) - 1; g = 0
    for i in range(ei+1, min(ei+tc+1, mx+1)):
        g = g+1 if data[i]['green'] else 0
        if g >= 2:
            xi = min(i+1, mx)
            p = data[xi]['o']
            pnl = (p-ep)/ep*100
            return {'x':'2g','pnl':pnl,'d':xi-ei,'entry_price':ep,'exit_price':p}
    xi = min(ei+tc+1, mx)
    p = data[xi]['o']
    pnl = (p-ep)/ep*100
    return {'x':'tc','pnl':pnl,'d':xi-ei,'entry_price':ep,'exit_price':p}

def check_trigger(assets, day_maps, date, tier):
    """Check if tier triggers on given date."""
    aa = tier['anchor_asset']
    ah = tier['anchor']
    if date not in day_maps[aa] or ah not in day_maps[aa][date]:
        return False
    ai, ac = day_maps[aa][date][ah]
    if not ac['red'] or ac['range_pct'] < tier['min_rng']:
        return False
    reds = 0
    for off in range(tier['win']):
        h = ah + off
        if h in day_maps[aa][date]:
            _, bar = day_maps[aa][date][h]
            if bar['red']:
                reds += 1
    return reds >= tier['rt']

def get_position_size(tier_name, asset):
    """Get Kelly-based position size for a tier."""
    kelly = KELLY_MULTIPLIERS.get(tier_name, 0)
    if kelly == 0:
        return 0, 0
    position = BASE_POSITION * kelly
    lots = position / AVG_PRICES[asset]
    return position, lots

def generate_trades(tiers_to_use=None, priority_cascade=True):
    """Generate all trades with Kelly sizing. No theoretical caps."""
    assets, day_maps, dates = load_data()
    use_tiers = tiers_to_use or TIERS
    
    all_trades = []
    
    for date in dates:
        claimed = {}
        
        for tier in use_tiers:
            if not check_trigger(assets, day_maps, date, tier):
                continue
            
            ah, win = tier['anchor'], tier['win']
            
            for ta, eh, tc in tier['entries']:
                if eh < ah + win:
                    continue
                if priority_cascade and ta in claimed:
                    continue
                if date not in day_maps[ta] or eh not in day_maps[ta][date]:
                    continue
                
                position, lots = get_position_size(tier['name'], ta)
                if position == 0:
                    continue
                
                ei, ec = day_maps[ta][date][eh]
                ep = ec['o']
                res = sim_2g(assets[ta], ei, ep, tc)
                
                pnl_dollar = position * (res['pnl'] / 100)
                
                trade = {
                    'date': date,
                    'tier': tier['name'],
                    'asset': ta,
                    'entry_hour': eh,
                    'time_cap': tc,
                    'pnl': res['pnl'],
                    'pnl_dollar': pnl_dollar,
                    'position': position,
                    'lots': lots,
                    'kelly': KELLY_MULTIPLIERS.get(tier['name'], 0),
                    'exit_type': res['x'],
                }
                all_trades.append(trade)
                
                if priority_cascade:
                    claimed[ta] = tier['name']
    
    return all_trades

# ══════════════════════════════════════════════════════════════════════════════
# REPORTING
# ══════════════════════════════════════════════════════════════════════════════
def report_combined():
    """Report combined system stats."""
    # No theoretical caps - only historical data matters
    trades = generate_trades(priority_cascade=True)
    
    print("="*80)
    print("26-TIER SYSTEM v3.0 — KELLY SIZING")
    print("="*80)
    
    wins = sum(1 for t in trades if t['pnl'] > 0)
    total_pnl_pct = sum(t['pnl'] for t in trades)
    total_pnl_dollar = sum(t['pnl_dollar'] for t in trades)
    worst_pct = min(t['pnl'] for t in trades)
    worst_dollar = min(t['pnl_dollar'] for t in trades)
    
    print(f"\n  Trades: {len(trades)} | WR: {wins/len(trades)*100:.1f}%")
    print(f"  Total P&L: {total_pnl_pct:+.1f}% raw | ${total_pnl_dollar:+,.0f} Kelly-weighted")
    print(f"  Avg/trade: {total_pnl_pct/len(trades):+.2f}% | ${total_pnl_dollar/len(trades):+,.0f}")
    print(f"  Worst: {worst_pct:+.2f}% | ${worst_dollar:+,.0f}")
    print(f"  Trades/month: {len(trades)/4.17/12:.1f}")
    
    # By year
    print("\n  Annual (Kelly-weighted $):")
    by_year = defaultdict(lambda: {'n':0,'w':0,'pnl':0,'pnl_dollar':0})
    for t in trades:
        y = t['date'].year
        by_year[y]['n'] += 1
        if t['pnl'] > 0:
            by_year[y]['w'] += 1
        by_year[y]['pnl'] += t['pnl']
        by_year[y]['pnl_dollar'] += t['pnl_dollar']
    
    for y in sorted(by_year.keys()):
        s = by_year[y]
        wr = s['w']/s['n']*100
        print(f"    {y}: {s['n']} trades, {wr:.0f}% WR, {s['pnl']:+.1f}%, ${s['pnl_dollar']:+,.0f}")
    
    # Daily exposure analysis
    print("\n  Daily Exposure Analysis:")
    by_date = defaultdict(list)
    for t in trades:
        by_date[t['date']].append(t)
    
    max_daily_loss = 0
    worst_day = None
    for date, day_trades in by_date.items():
        daily_loss = sum(t['pnl_dollar'] for t in day_trades if t['pnl_dollar'] < 0)
        if daily_loss < max_daily_loss:
            max_daily_loss = daily_loss
            worst_day = date
    
    print(f"    Worst daily loss: ${max_daily_loss:,.0f} on {worst_day}")
    print(f"    Days with 2+ trades: {sum(1 for ts in by_date.values() if len(ts) >= 2)}")
    print(f"    Days with 3 trades: {sum(1 for ts in by_date.values() if len(ts) >= 3)}")

def report_kelly():
    """Detailed Kelly analysis."""
    trades = generate_trades(priority_cascade=True)
    
    print("="*80)
    print("KELLY SIZING ANALYSIS")
    print("="*80)
    
    print(f"\n{'Tier':<5} {'Kelly':<6} {'Trades':<7} {'WR':<5} {'Avg $':<8} {'Total $':<10} {'Worst $':<9}")
    print("-"*60)
    
    by_tier = defaultdict(list)
    for t in trades:
        by_tier[t['tier']].append(t)
    
    for tier in sorted(by_tier.keys()):
        ts = by_tier[tier]
        wins = sum(1 for t in ts if t['pnl'] > 0)
        wr = wins / len(ts) * 100
        total_dollar = sum(t['pnl_dollar'] for t in ts)
        avg_dollar = total_dollar / len(ts)
        worst_dollar = min(t['pnl_dollar'] for t in ts)
        kelly = ts[0]['kelly']
        
        print(f"{tier:<5} {kelly:<6.2f} {len(ts):<7} {wr:<5.0f}% ${avg_dollar:<+7,.0f} ${total_dollar:<+9,.0f} ${worst_dollar:<+8,.0f}")
    
    print("-"*60)
    total = sum(t['pnl_dollar'] for t in trades)
    avg = total / len(trades)
    worst = min(t['pnl_dollar'] for t in trades)
    print(f"{'TOTAL':<5} {'—':<6} {len(trades):<7} {sum(1 for t in trades if t['pnl']>0)/len(trades)*100:<5.0f}% ${avg:<+7,.0f} ${total:<+9,.0f} ${worst:<+8,.0f}")

def report_eval(start_year=None, verbose=False):
    """Simulate $100K prop eval with Kelly sizing."""
    trades = generate_trades(priority_cascade=True)
    
    print("="*80)
    print("EVAL SIM — Kelly Sizing (Historical Data)")
    print("Goal: +$10K | Bust: -$3K daily")
    print("="*80)
    
    by_year = defaultdict(list)
    for t in trades:
        by_year[t['date'].year].append(t)
    
    for year in sorted(by_year.keys()):
        if start_year and year < start_year:
            continue
        
        balance = 100000
        peak = balance
        max_dd = 0
        
        year_trades = sorted(by_year[year], key=lambda x: x['date'])
        
        print(f"\n  Starting {year}:")
        
        if verbose:
            print(f"\n    # |       Date | Tier |  Asset |  Kelly | Position |    P&L$ |  Balance |    DD$")
            print("  " + "-"*85)
        
        for i, t in enumerate(year_trades, 1):
            if balance >= 110000:
                break
            if balance <= 97000:
                print(f"    ❌ BUSTED at ${balance:,.0f}")
                break
            
            balance += t['pnl_dollar']
            peak = max(peak, balance)
            dd = peak - balance
            max_dd = max(max_dd, dd)
            
            if verbose:
                print(f"  {i:3} | {t['date']} | {t['tier']:>4} | {t['asset']:>6} | {t['kelly']:>6.2f} | ${t['position']:>7,.0f} | ${t['pnl_dollar']:>+7,.0f} | ${balance:>8,.0f} | ${dd:>6,.0f}")
        
        print(f"    Trades: {len(year_trades)} | Balance: ${balance:,.0f} | Max DD: ${max_dd:,.0f}")
        if balance >= 110000:
            print("    ✅ PASSED")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['combined','kelly','eval','all'], default='combined')
    parser.add_argument('--year', type=int)
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()
    
    if args.mode == 'combined' or args.mode == 'all':
        report_combined()
    if args.mode == 'kelly' or args.mode == 'all':
        report_kelly()
    if args.mode == 'eval' or args.mode == 'all':
        report_eval(start_year=args.year, verbose=args.verbose)

if __name__ == "__main__":
    main()
