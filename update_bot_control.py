# update_bot_control.py
import json
import os

def update_bot_control():
    """Update bot_control.json with better settings"""
    
    settings = {
        "running": True,
        "simulation_mode": True,
        "filter_fake_tokens": False,
        "use_birdeye_api": True,
        "use_machine_learning": True,
        "take_profit_target": 1.15,
        "stop_loss_percentage": 0.05,
        "trailing_stop_enabled": True,
        "trailing_stop_percentage": 0.03,
        "max_investment_per_token": 0.5,
        "min_investment_per_token": 0.1,
        "max_open_positions": 5,
        "slippage_tolerance": 0.1,
        "MIN_SAFETY_SCORE": 0.0,
        "MIN_VOLUME": 1000.0,
        "MIN_LIQUIDITY": 5000.0,
        "MIN_MCAP": 10000.0,
        "MIN_HOLDERS": 10,
        "MIN_PRICE_CHANGE_1H": -50.0,
        "MIN_PRICE_CHANGE_6H": -50.0,
        "MIN_PRICE_CHANGE_24H": -50.0,
        "MAX_PRICE_CHANGE_24H": 1000.0,
        "max_daily_loss_percentage": 0.1,
        "max_drawdown_percentage": 0.2,
        "starting_simulation_balance": 10.0,
        "stop_loss_percentage_display": 5.0,
        "slippage_tolerance_display": 10.0,
        "real_wallet_address": "16um9NG9V88CWR9vESe42WfmNrDcTNq9jUit5t5mpgf",
        "real_wallet_starting_balance": 2.0,
        "monitor_real_wallet": True
    }
    
    with open('bot_control.json', 'w') as f:
        json.dump(settings, f, indent=4)
    
    print("✅ Updated bot_control.json")

if __name__ == "__main__":
    update_bot_control()