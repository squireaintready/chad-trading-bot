#!/usr/bin/env python3
"""
Chad Trading Bot — Discord edition
- /sta : Quick status (building tiers + positions + P&L)
- /sum : Full day summary by anchor hour
- Auto-alerts + auto-execution at signal hours
"""

import os
import sys
import subprocess
import json
import asyncio
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).parent
TOOLS_DIR = ROOT_DIR / "tools"
SIGNAL_SCRIPT = TOOLS_DIR / "signal-check.py"
STATE_FILE = TOOLS_DIR / ".bot-state.json"

# Load .env
env_file = ROOT_DIR / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

# ── EST helper ──────────────────────────────────────────────────────────────
def get_est_now():
    utc_now = datetime.now(timezone.utc)
    y = utc_now.year
    mar1 = datetime(y, 3, 1, tzinfo=timezone.utc)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7, hours=7)
    nov1 = datetime(y, 11, 1, tzinfo=timezone.utc)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7, hours=6)
    off = -4 if dst_start <= utc_now < dst_end else -5
    return utc_now + timedelta(hours=off)

# ── Run signal-check.py ────────────────────────────────────────────────────
def run_signal_check(mode=None):
    cmd = [sys.executable, str(SIGNAL_SCRIPT)]
    if mode:
        cmd.append(f"--{mode}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() or result.stderr.strip() or "No output"
    except subprocess.TimeoutExpired:
        return "Signal check timed out"
    except Exception as e:
        return f"Error: {e}"

# ── Auto-execution ─────────────────────────────────────────────────────────
AUTO_EXECUTE = os.environ.get("AUTO_EXECUTE", "false").lower() == "true"

async def execute_trade(action, asset, lots=0, tier=""):
    """Execute a trade via Playwright and return result message."""
    try:
        from tools.executor import open_position, close_position
        if action == "open":
            ok, msg = await open_position(asset, lots)
            emoji = "✅" if ok else "❌"
            return f"{emoji} **{tier} ENTRY:** {asset} {lots} lots\n{msg}"
        elif action == "close":
            ok, msg = await close_position(asset)
            emoji = "✅" if ok else "❌"
            return f"{emoji} **{tier} EXIT:** {asset}\n{msg}"
    except Exception as e:
        return f"❌ Execution error: {e}"

# ── Parse signal-check output for actionable signals ───────────────────────
def parse_entry_signals(output):
    """Parse signal-check auto output for entry signals."""
    signals = []
    lines = output.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if 'ENTRY SIGNALS' in line:
            # Parse following lines for trade details
            while i + 1 < len(lines):
                i += 1
                l = lines[i].strip()
                if not l or l.startswith('📤') or l.startswith('🔔'):
                    break
                if 'BUY' in l:
                    # "BB1: BUY ETH @ $2,450.00"
                    parts = l.split()
                    tier = parts[0].rstrip(':')
                    asset = parts[2]
                    price = parts[4].replace('$', '').replace(',', '')
                elif 'Position:' in l:
                    parts = l.split('|')
                    pos_str = parts[0].split('$')[1].strip().replace(',', '')
                    lots_str = parts[1].split(':')[1].strip()
                    signals.append({
                        'tier': tier, 'asset': asset,
                        'lots': float(lots_str), 'price': float(price)
                    })
        i += 1
    return signals

def parse_exit_signals(output):
    """Parse signal-check auto output for exit signals."""
    exits = []
    lines = output.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if 'EXIT SIGNALS' in line:
            while i + 1 < len(lines):
                i += 1
                l = lines[i].strip()
                if not l:
                    break
                # "✅ BB1 ETH: 2_green" or "🔴 BB1 ETH: time_cap"
                if any(l.startswith(e) for e in ('✅', '🔴')):
                    parts = l.split()
                    tier = parts[1]
                    asset = parts[2].rstrip(':')
                    exits.append({'tier': tier, 'asset': asset})
        i += 1
    return exits

# ── Bot setup ──────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ALERT_CHANNEL_ID = int(os.environ.get("ALERT_CHANNEL_ID", "0"))

def get_alert_channel():
    """Find the channel to post alerts in."""
    if ALERT_CHANNEL_ID:
        ch = bot.get_channel(ALERT_CHANNEL_ID)
        if ch:
            return ch
    for guild in bot.guilds:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                return ch
    return None

@bot.event
async def on_ready():
    print(f"Chad online: {bot.user} | Servers: {len(bot.guilds)}", flush=True)
    print(f"Auto-execute: {AUTO_EXECUTE}", flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands", flush=True)
    except Exception as e:
        print(f"Slash sync failed: {e}", flush=True)
    if not hourly_check.is_running():
        hourly_check.start()

# ── Slash commands ─────────────────────────────────────────────────────────
@bot.tree.command(name="sta", description="Quick status: building tiers + positions + P&L")
async def sta(interaction: discord.Interaction):
    await interaction.response.defer()
    output = run_signal_check("status")
    if len(output) > 1900:
        output = output[:1900] + "\n... (truncated)"
    await interaction.followup.send(f"```\n{output}\n```")

@bot.tree.command(name="sum", description="Full day summary: all tiers by anchor hour")
async def summary(interaction: discord.Interaction):
    await interaction.response.defer()
    output = run_signal_check("summary")
    if len(output) > 1900:
        output = output[:1900] + "\n... (truncated)"
    await interaction.followup.send(f"```\n{output}\n```")

# ── Text commands (!sta, !sum) ─────────────────────────────────────────────
@bot.command(name="sta")
async def sta_text(ctx):
    output = run_signal_check("status")
    if len(output) > 1900:
        output = output[:1900] + "\n... (truncated)"
    await ctx.send(f"```\n{output}\n```")

@bot.command(name="sum")
async def sum_text(ctx):
    output = run_signal_check("summary")
    if len(output) > 1900:
        output = output[:1900] + "\n... (truncated)"
    await ctx.send(f"```\n{output}\n```")

# ── Hourly auto-check + execution ─────────────────────────────────────────
@tasks.loop(minutes=1)
async def hourly_check():
    now = get_est_now()
    # Run at :01 past the hour, 9am-11pm EST
    if now.minute != 1 or now.hour < 9 or now.hour > 23:
        return

    output = run_signal_check()
    if output == "HEARTBEAT_OK":
        return

    channel = get_alert_channel()
    if not channel:
        return

    # Post signal check results
    if len(output) > 1900:
        output = output[:1900] + "\n... (truncated)"
    await channel.send(f"```\n{output}\n```")

    # Auto-execute if enabled
    if AUTO_EXECUTE:
        # Check for entry signals
        entries = parse_entry_signals(output)
        for sig in entries:
            await channel.send(f"⚡ **EXECUTING ENTRY:** {sig['tier']} {sig['asset']} {sig['lots']:.2f} lots...")
            result = await execute_trade("open", sig['asset'], sig['lots'], sig['tier'])
            await channel.send(result)

        # Check for exit signals
        exits = parse_exit_signals(output)
        for sig in exits:
            await channel.send(f"⚡ **EXECUTING EXIT:** {sig['tier']} {sig['asset']}...")
            result = await execute_trade("close", sig['asset'], tier=sig['tier'])
            await channel.send(result)

# ── Start ──────────────────────────────────────────────────────────────────
def main():
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        token_file = ROOT_DIR / ".discord-token"
        if token_file.exists():
            token = token_file.read_text().strip()
    if not token:
        print("No token found! Set DISCORD_BOT_TOKEN in .env")
        return
    bot.run(token)

if __name__ == "__main__":
    main()
