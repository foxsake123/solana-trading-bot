# quick_dashboard_fix.py - Quick fix for the dashboard

import os

def fix_enhanced_dashboard():
    """Fix the enhanced dashboard file"""
    # Find the dashboard file
    dashboard_file = os.path.join('dashboard', 'enhanced_dashboard.py')
    if not os.path.exists(dashboard_file):
        print(f"Error: Could not find {dashboard_file}")
        return False
    
    # Create a backup
    backup_file = f"{dashboard_file}.bak"
    try:
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Save backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Created backup at {backup_file}")
    except Exception as e:
        print(f"Error backing up file: {e}")
        # Try without encoding
        try:
            with open(dashboard_file, 'r') as f:
                content = f.read()
            
            with open(backup_file, 'w') as f:
                f.write(content)
            
            print(f"Created backup at {backup_file}")
        except Exception as e:
            print(f"Error backing up file: {e}")
            return False
    
    # Split into lines
    lines = content.split('\n')
    
    # Find functions without body (defs followed by non-indented lines)
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        fixed_lines.append(line)
        
        # Check if this is a function definition
        if line.lstrip().startswith('def ') and line.rstrip().endswith(':'):
            # Look at the next line
            if i+1 < len(lines):
                next_line = lines[i+1]
                # If next line is not indented and not empty, add a 'pass' statement
                if next_line.strip() and not next_line.startswith(' ') and not next_line.startswith('\t'):
                    # Extract indentation from current line
                    indent = ''
                    for c in line:
                        if c == ' ' or c == '\t':
                            indent += c
                        else:
                            break
                    
                    # Add pass statement with indentation
                    fixed_lines.append(f"{indent}    pass")
                    print(f"Added 'pass' after function on line {i+1}")
        
        i += 1
    
    # Write fixed content
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))
    
    print(f"Fixed {dashboard_file}")
    return True

def create_simple_dashboard():
    """Create a simple dashboard file"""
    simple_content = """
import streamlit as st
import pandas as pd
import os
import json
import time

def display_dashboard():
    st.set_page_config(
        page_title="Solana Trading Bot",
        page_icon="💸",
        layout="wide"
    )
    
    st.title("Solana Trading Bot - Simple Dashboard")
    
    # Load bot control settings
    control_file = 'data/bot_control.json'
    if not os.path.exists(control_file):
        control_file = 'bot_control.json'
        
    bot_settings = {}
    if os.path.exists(control_file):
        try:
            with open(control_file, 'r') as f:
                bot_settings = json.load(f)
        except:
            st.error(f"Could not load {control_file}")
    
    # Display status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Bot Status", 
                "Running" if bot_settings.get('running', False) else "Stopped")
    
    with col2:
        st.metric("Mode", 
                "Simulation" if bot_settings.get('simulation_mode', True) else "Real Trading")
    
    with col3:
        st.metric("Last Updated", time.strftime("%H:%M:%S"))
    
    # Display bot settings
    st.subheader("Bot Settings")
    st.json(bot_settings)
    
    # Try to load trades
    try:
        import sqlite3
        
        # Find database file
        db_file = 'data/sol_bot.db'
        if not os.path.exists(db_file):
            db_file = 'solana_trader.db'
        
        if os.path.exists(db_file):
            conn = sqlite3.connect(db_file)
            
            # Get active orders
            try:
                active_orders = pd.read_sql_query("SELECT * FROM trades WHERE action='BUY' ORDER BY timestamp DESC", conn)
                
                st.subheader("Active Positions")
                if not active_orders.empty:
                    st.dataframe(active_orders)
                else:
                    st.info("No active positions")
            except Exception as e:
                st.warning(f"Could not load active positions: {e}")
            
            # Get recent trades
            try:
                trades = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 20", conn)
                
                st.subheader("Recent Trades")
                if not trades.empty:
                    st.dataframe(trades)
                else:
                    st.info("No trades found")
            except Exception as e:
                st.warning(f"Could not load trades: {e}")
            
            conn.close()
        else:
            st.warning(f"Database file not found: {db_file}")
            
    except Exception as e:
        st.error(f"Error accessing database: {e}")
    
    # Add refresh button
    if st.button("Refresh Dashboard"):
        st.experimental_rerun()

if __name__ == "__main__":
    display_dashboard()
"""
    
    simple_file = os.path.join('dashboard', 'simple_dashboard.py')
    with open(simple_file, 'w', encoding='utf-8') as f:
        f.write(simple_content)
    
    print(f"Created simple dashboard at {simple_file}")
    return simple_file

def main():
    print("=" * 60)
    print("DASHBOARD FIX")
    print("=" * 60)
    print()
    
    print("1. Fixing enhanced_dashboard.py...")
    fixed = fix_enhanced_dashboard()
    
    print()
    print("2. Creating simple dashboard...")
    simple_file = create_simple_dashboard()
    
    print()
    print("=" * 60)
    print("FIX COMPLETE!")
    print("=" * 60)
    print()
    print("You can now try:")
    print("1. Run the fixed enhanced dashboard:")
    print("   streamlit run dashboard/enhanced_dashboard.py")
    print()
    print("2. Or use the simple dashboard:")
    print("   streamlit run dashboard/simple_dashboard.py")
    print()
    print("3. Or try one of the existing dashboards:")
    print("   streamlit run dashboard/dashboard_patched.py")
    print("   streamlit run dashboard/robust_dashboard.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
