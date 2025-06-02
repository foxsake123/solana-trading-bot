# update_run_bot_to_use_real.py
import os

def update_run_bot():
    """Update run_bot_updated.py to import the real trading bot"""
    
    with open('run_bot_updated.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update the import
    old_import = "from core.simplified_trading_bot import TradingBot"
    new_import = "from core.real_trading_bot import TradingBot"
    
    content = content.replace(old_import, new_import)
    
    with open('run_bot_updated.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Updated run_bot_updated.py to use real_trading_bot")

if __name__ == "__main__":
    update_run_bot()