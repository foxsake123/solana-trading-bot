# fix_dashboard.py - Fix indentation errors in enhanced_dashboard.py

import os
import sys
import logging
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fix_dashboard')

def fix_enhanced_dashboard():
    """Fix the enhanced_dashboard.py file"""
    # Find the dashboard file
    dashboard_file = os.path.join('dashboard', 'enhanced_dashboard.py')
    if not os.path.exists(dashboard_file):
        logger.error(f"Could not find {dashboard_file}")
        return False
    
    # Create a backup
    backup_file = f"{dashboard_file}.bak"
    try:
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Save backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created backup at {backup_file}")
    except:
        # Try different encoding if UTF-8 fails
        try:
            with open(dashboard_file, 'r') as f:
                content = f.read()
            
            # Save backup
            with open(backup_file, 'w') as f:
                f.write(content)
            
            logger.info(f"Created backup at {backup_file}")
        except Exception as e:
            logger.error(f"Could not read or backup {dashboard_file}: {e}")
            return False
    
    # Find the error around line 1488
    lines = content.split('\n')
    
    # Find the problematic function definition
    error_line_num = None
    for i, line in enumerate(lines):
        if i >= 1485 and i <= 1495:  # Check lines around the reported error
            if line.strip().startswith('def ') and i + 1 < len(lines) and lines[i + 1].strip().startswith('"""'):
                error_line_num = i
                break
    
    if error_line_num is None:
        # If we can't find by exact pattern, look for any function def followed by docstring
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') and i + 1 < len(lines) and lines[i + 1].strip().startswith('"""'):
                # Check if there's no indented code after the docstring
                j = i + 2
                while j < len(lines) and (lines[j].strip().startswith('"""') or lines[j].strip() == "" or lines[j].strip().startswith('#')):
                    j += 1
                
                if j < len(lines) and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                    error_line_num = i
                    break
    
    if error_line_num is None:
        logger.error("Could not find the exact error location. Trying general fixes...")
        
        # Try to fix any empty function by adding a pass statement
        fixed_content = re.sub(r'def\s+([^(]*)\([^)]*\):\s*(?:"""[^"]*""")?\s*(?=\S)', 
                             r'def \1():\n    pass\n', 
                             content)
        
        # Write the fixed content
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        logger.info(f"Applied general fixes to {dashboard_file}")
        return True
    
    # Found the error, now fix it
    logger.info(f"Found error at line {error_line_num + 1}: {lines[error_line_num]}")
    
    # Add a 'pass' statement with proper indentation after the docstring
    # First determine the end of docstring
    docstring_start = error_line_num + 1
    docstring_end = docstring_start
    
    # Find the end of the docstring
    in_docstring = True
    for i in range(docstring_start + 1, len(lines)):
        if '"""' in lines[i]:
            docstring_end = i
            break
    
    # Determine indentation level
    indent = ""
    if error_line_num > 0 and lines[error_line_num - 1].strip():
        prev_line = lines[error_line_num - 1]
        indent = re.match(r'^(\s*)', prev_line).group(1) + "    "
    else:
        indent = "    "  # Default indentation
    
    # Insert pass statement after docstring
    if docstring_end >= docstring_start:
        lines.insert(docstring_end + 1, f"{indent}pass")
        logger.info(f"Added 'pass' statement after docstring at line {docstring_end + 1}")
    else:
        # If we can't find docstring end, add pass after function def
        lines.insert(error_line_num + 1, f"{indent}pass")
        logger.info(f"Added 'pass' statement after function definition at line {error_line_num + 1}")
    
    # Write the fixed content
    fixed_content = '\n'.join(lines)
    
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    logger.info(f"Fixed {dashboard_file}")
    return True

def create_simple_dashboard():
    """Create a very simple dashboard as a fallback"""
    simple_dashboard = """
import streamlit as st
import pandas as pd
import os
import json
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simple_dashboard')

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_bot_control():
    """Load bot control settings"""
    control_file = 'data/bot_control.json'
    if not os.path.exists(control_file):
        control_file = 'bot_control.json'
    
    if os.path.exists(control_file):
        try:
            with open(control_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading bot control: {e}")
    
    return {
        'running': False,
        'simulation_mode': True
    }

def load_positions():
    """Load active positions"""
    try:
        # Try to use the database module
        try:
            from database import Database
            db = Database()
            positions = db.get_active_orders()
            if not isinstance(positions, pd.DataFrame):
                positions = pd.DataFrame(positions)
            return positions
        except Exception as e:
            logger.error(f"Error using database module: {e}")
        
        # Fallback to direct DB query
        import sqlite3
        conn = sqlite3.connect('data/sol_bot.db')
        positions = pd.read_sql_query("SELECT * FROM trades WHERE action='BUY'", conn)
        conn.close()
        return positions
    except Exception as e:
        logger.error(f"Error loading positions: {e}")
        return pd.DataFrame()

def load_trades():
    """Load recent trades"""
    try:
        # Try to use the database module
        try:
            from database import Database
            db = Database()
            trades = db.get_trade_history(limit=50)
            if not isinstance(trades, pd.DataFrame):
                trades = pd.DataFrame(trades)
            return trades
        except Exception as e:
            logger.error(f"Error using database module: {e}")
        
        # Fallback to direct DB query
        import sqlite3
        conn = sqlite3.connect('data/sol_bot.db')
        trades = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        return trades
    except Exception as e:
        logger.error(f"Error loading trades: {e}")
        return pd.DataFrame()

def load_wallet_balance():
    """Load wallet balance"""
    try:
        # Try to get SOL price
        try:
            import httpx
            response = httpx.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd")
            sol_price = response.json()['solana']['usd']
        except:
            sol_price = 173.0
        
        # For now, return dummy balance
        return {
            'sol': 1.0,
            'usd': 1.0 * sol_price
        }
    except Exception as e:
        logger.error(f"Error getting wallet balance: {e}")
        return {
            'sol': 0.0,
            'usd': 0.0
        }

def display_dashboard():
    """Display the dashboard"""
    st.set_page_config(
        page_title="Solana Trading Bot",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("Solana Trading Bot Dashboard")
    
    # Load data
    control = load_bot_control()
    positions = load_positions()
    trades = load_trades()
    wallet = load_wallet_balance()
    
    # Create columns for status indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Bot Status", "Running" if control.get('running', False) else "Paused")
    
    with col2:
        st.metric("Mode", "Simulation" if control.get('simulation_mode', True) else "Real Trading")
    
    with col3:
        st.metric("Wallet Balance", f"{wallet['sol']:.4f} SOL (${wallet['usd']:.2f})")
    
    # Display positions
    st.header("Active Positions")
    if not positions.empty:
        st.dataframe(positions)
    else:
        st.info("No active positions")
    
    # Display trades
    st.header("Recent Trades")
    if not trades.empty:
        st.dataframe(trades)
    else:
        st.info("No trades recorded")
    
    # Display bot controls
    st.header("Bot Controls")
    st.json(control)

if __name__ == "__main__":
    display_dashboard()
"""
    
    simple_file = os.path.join('dashboard', 'simple_fallback_dashboard.py')
    with open(simple_file, 'w', encoding='utf-8') as f:
        f.write(simple_dashboard)
    
    logger.info(f"Created simple fallback dashboard at {simple_file}")
    return simple_file

def main():
    """Main function"""
    print("=" * 60)
    print("DASHBOARD FIX")
    print("=" * 60)
    print()
    
    print("1. Fixing enhanced_dashboard.py...")
    fixed = fix_enhanced_dashboard()
    if fixed:
        print("   Successfully fixed enhanced_dashboard.py")
    else:
        print("   Could not fix enhanced_dashboard.py")
    print()
    
    print("2. Creating simple fallback dashboard...")
    simple_dashboard = create_simple_dashboard()
    print(f"   Created {simple_dashboard}")
    print()
    
    print("=" * 60)
    print("FIX COMPLETE!")
    print("=" * 60)
    print()
    print("You can now try these options:")
    print("1. Run the fixed enhanced dashboard:")
    print("   streamlit run dashboard/enhanced_dashboard.py")
    print()
    print("2. If that doesn't work, try the simple fallback dashboard:")
    print("   streamlit run dashboard/simple_fallback_dashboard.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
