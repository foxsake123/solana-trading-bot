# find_trading_bot.py
import os
import glob

def find_trading_bot_files():
    """Find all trading bot files and check which one is being used"""
    
    patterns = [
        "*trading_bot*.py",
        "core/*trading_bot*.py"
    ]
    
    for pattern in patterns:
        files = glob.glob(pattern)
        for file in files:
            if os.path.exists(file):
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for the problematic code
                if 'SIM: Bought' in content or 'Sim0TopGainer' in content:
                    print(f"\n❌ Found simulation code in: {file}")
                    
                    # Show the problematic section
                    for i, line in enumerate(content.split('\n')):
                        if 'Sim' in line and ('TopGainer' in line or 'SIM:' in line):
                            print(f"   Line {i+1}: {line.strip()}")
                            
                    # Check if this is the simplified_trading_bot
                    if 'class TradingBot:' in content:
                        print(f"   This appears to be the main TradingBot class")

if __name__ == "__main__":
    find_trading_bot_files()