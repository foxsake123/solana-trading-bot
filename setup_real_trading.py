import json
import os

print("=== SOLANA TRADING BOT - REAL TRADING SETUP ===")
print("\nThis script will configure your bot for real trading.")
print("WARNING: Real trading involves financial risk.\n")

# Load current settings
try:
    with open('bot_control.json', 'r') as f:
        settings = json.load(f)
except Exception:
    settings = {}

# Configure essential settings
settings['running'] = False  # Start paused for safety
settings['simulation_mode'] = False
settings['filter_fake_tokens'] = True

# Trading parameters
print("\n== Trading Parameters ==")
print("Configure how much you want to invest per trade and your profit/loss targets.")

# Max investment
current = settings.get('max_investment_per_token', 0.1)
max_investment = float(input(f"Maximum investment per token in SOL (current: {current}): ") or current)
settings['max_investment_per_token'] = max_investment

# Take profit
current = settings.get('take_profit_target', 15.0)
take_profit = float(input(f"Take profit percentage (current: {current}%): ") or current)
settings['take_profit_target'] = take_profit

# Stop loss
current = settings.get('stop_loss_percentage', 7.5)
stop_loss = float(input(f"Stop loss percentage (current: {current}%): ") or current)
settings['stop_loss_percentage'] = stop_loss

# Token filters
print("\n== Token Filtering ==")
print("Higher minimum values = less risk but fewer trading opportunities")

# Minimum liquidity
current = settings.get('MIN_LIQUIDITY', 50000)
min_liq = float(input(f"Minimum liquidity in USD (current: ${current}): ") or current)
settings['MIN_LIQUIDITY'] = min_liq

# Minimum 24h volume
current = settings.get('MIN_VOLUME', 10000)
min_vol = float(input(f"Minimum 24h volume in USD (current: ${current}): ") or current)
settings['MIN_VOLUME'] = min_vol

# Save settings
with open('bot_control.json', 'w') as f:
    json.dump(settings, f, indent=4)

print("\nSettings saved to bot_control.json")
print("\nREMINDER: The bot is set to 'not running'. To start it:")
print("1. Verify all settings in bot_control.json")
print("2. Set 'running': true when you're ready to begin")
print("3. Run 'python main.py' to start the bot")