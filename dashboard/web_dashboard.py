"""
Solana Trading Bot Dashboard for monitoring bot status and trading activity
"""
import os
import sys
import logging
import time
import json
import datetime
import argparse
import threading
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Try to import dash components for the web dashboard
try:
    import dash
    from dash import dcc, html, callback, Input, Output, State
    import dash_bootstrap_components as dbc
    import plotly.graph_objects as go
    import plotly.express as px
    from flask import Flask
    HAS_DASH = True
except ImportError:
    HAS_DASH = False
    print("Dash not available. Install with: pip install dash dash-bootstrap-components plotly")

# Try to import pandas for data handling
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Pandas not available. Install with: pip install pandas")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('dashboard')

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import configuration with fallback
try:
    # Try importing from config_adapter first
    try:
        from config_adapter import (
            MAINNET_RPC_URL,
            WALLET_PRIVATE_KEY,
            BOT_RUNNING,
            SIMULATION_MODE,
            TRADING_PARAMS,
        )
        logger.info("Imported configuration from config_adapter")
    except ImportError:
        # Try importing from config directly as fallback
        from config import (
            MAINNET_RPC_URL,
            WALLET_PRIVATE_KEY,
            BOT_RUNNING,
            SIMULATION_MODE,
            TRADING_PARAMS,
        )
        logger.info("Imported configuration from config")
except ImportError:
    # Default values
    MAINNET_RPC_URL = "https://api.mainnet-beta.solana.com"
    WALLET_PRIVATE_KEY = ""
    BOT_RUNNING = False
    SIMULATION_MODE = True
    TRADING_PARAMS = {}
    logger.warning("Using default configuration values")

# Try to import SoldersAdapter for wallet functions
try:
    from SoldersAdapter import SoldersAdapter
    HAS_SOLDERS_ADAPTER = True
except ImportError:
    HAS_SOLDERS_ADAPTER = False
    logger.warning("SoldersAdapter not available")

# Try to import Database class for trading history
try:
    from database import Database
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    logger.warning("Database not available")

# Constants
LOG_FILE = os.path.join(project_root, 'logs', 'trading_bot.log')
BOT_CONTROL_FILE = os.path.join(project_root, 'bot_control.json')
DASHBOARD_PORT = 8050
REFRESH_INTERVAL = 10000  # 10 seconds in milliseconds

class DashboardData:
    """Class to collect and manage data for the dashboard"""
    
    def __init__(self):
        """Initialize dashboard data"""
        self.wallet_address = None
        self.wallet_balance_sol = 0.0
        self.wallet_balance_usd = 0.0
        self.sol_price = 0.0
        self.bot_running = False
        self.simulation_mode = True
        self.trading_params = {}
        self.active_positions = []
        self.recent_trades = []
        self.recent_logs = []
        self.profit_loss = {'sol': 0.0, 'usd': 0.0, 'percent': 0.0}
        self.tokens_scanned = 0
        self.trades_today = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.uptime = 0
        self.start_time = time.time()
        self.profit_loss_history = []
        self.balance_history = []
        self.token_data = []
        self.error_count = 0
        self.warning_count = 0
        
        # Get initial data
        self.reload_data()
        
    def reload_data(self):
        """Reload all dashboard data"""
        self.uptime = int(time.time() - self.start_time)
        self.load_wallet_data()
        self.load_bot_status()
        self.load_trading_data()
        self.load_logs()
        
    def load_wallet_data(self):
        """Load wallet data"""
        if HAS_SOLDERS_ADAPTER:
            try:
                adapter = SoldersAdapter()
                if adapter.init_wallet(WALLET_PRIVATE_KEY):
                    self.wallet_address = adapter.get_wallet_address()
                    self.wallet_balance_sol = adapter.get_wallet_balance()
                    self.sol_price = adapter.get_sol_price()
                    self.wallet_balance_usd = self.wallet_balance_sol * self.sol_price
                    
                    # Add to balance history
                    timestamp = datetime.datetime.now().isoformat()
                    self.balance_history.append({
                        'timestamp': timestamp,
                        'sol': self.wallet_balance_sol,
                        'usd': self.wallet_balance_usd,
                    })
                    
                    # Keep only the last 1000 points
                    if len(self.balance_history) > 1000:
                        self.balance_history = self.balance_history[-1000:]
            except Exception as e:
                logger.error(f"Error loading wallet data: {e}")
                
    def load_bot_status(self):
        """Load bot status from control file"""
        if os.path.exists(BOT_CONTROL_FILE):
            try:
                with open(BOT_CONTROL_FILE, 'r') as f:
                    control_data = json.load(f)
                    self.bot_running = control_data.get('running', False)
                    self.simulation_mode = control_data.get('simulation_mode', True)
                    
                    # Extract trading parameters
                    for param in ['initial_investment_sol', 'max_investment_per_token_sol', 
                                 'min_liquidity_usd', 'max_slippage_percent', 'buy_volume_threshold_usd',
                                 'min_price_change_percent', 'take_profit_percent', 'stop_loss_percent',
                                 'trailing_stop_percent']:
                        if param in control_data:
                            self.trading_params[param] = control_data[param]
            except Exception as e:
                logger.error(f"Error loading bot status: {e}")
        
    def load_trading_data(self):
        """Load trading data from database"""
        if HAS_DATABASE and HAS_PANDAS:
            try:
                db = Database()
                
                # Load active positions
                positions_df = db.get_active_orders()
                if not positions_df.empty:
                    self.active_positions = positions_df.to_dict('records')
                
                # Load recent trades
                trades_df = db.get_trading_history(limit=100)
                if not trades_df.empty:
                    self.recent_trades = trades_df.to_dict('records')
                    
                    # Calculate profit/loss
                    if 'gain_loss_sol' in trades_df.columns:
                        self.profit_loss['sol'] = trades_df['gain_loss_sol'].sum()
                        if self.sol_price > 0:
                            self.profit_loss['usd'] = self.profit_loss['sol'] * self.sol_price
                    
                    # Count trades today
                    today = datetime.datetime.now().date()
                    if 'timestamp' in trades_df.columns:
                        try:
                            trades_df['date'] = pd.to_datetime(trades_df['timestamp']).dt.date
                            self.trades_today = len(trades_df[trades_df['date'] == today])
                        except:
                            pass
                    
                    # Count successful trades
                    if 'action' in trades_df.columns:
                        sell_trades = trades_df[trades_df['action'] == 'SELL']
                        if 'gain_loss_sol' in sell_trades.columns:
                            self.successful_trades = len(sell_trades[sell_trades['gain_loss_sol'] > 0])
                            self.failed_trades = len(sell_trades[sell_trades['gain_loss_sol'] <= 0])
                
                # Load token data
                tokens_df = db.get_tokens(limit=100)
                if not tokens_df.empty:
                    self.token_data = tokens_df.to_dict('records')
                    self.tokens_scanned = len(tokens_df)
            except Exception as e:
                logger.error(f"Error loading trading data: {e}")
    
    def load_logs(self):
        """Load recent logs"""
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r') as f:
                    # Read last 100 lines
                    lines = f.readlines()[-100:]
                    self.recent_logs = lines
                    
                    # Count errors and warnings
                    self.error_count = sum(1 for line in lines if ' - ERROR - ' in line)
                    self.warning_count = sum(1 for line in lines if ' - WARNING - ' in line)
            else:
                # Check for logs in the current directory
                log_files = [f for f in os.listdir('.') if f.endswith('.log')]
                if log_files:
                    with open(log_files[0], 'r') as f:
                        lines = f.readlines()[-100:]
                        self.recent_logs = lines
                        
                        # Count errors and warnings
                        self.error_count = sum(1 for line in lines if ' - ERROR - ' in line)
                        self.warning_count = sum(1 for line in lines if ' - WARNING - ' in line)
        except Exception as e:
            logger.error(f"Error loading logs: {e}")
    
    def update_bot_control(self, running=None, simulation_mode=None, params=None):
        """Update bot control file"""
        if os.path.exists(BOT_CONTROL_FILE):
            try:
                # Read existing data
                with open(BOT_CONTROL_FILE, 'r') as f:
                    control_data = json.load(f)
                
                # Update values
                if running is not None:
                    control_data['running'] = running
                if simulation_mode is not None:
                    control_data['simulation_mode'] = simulation_mode
                if params:
                    for key, value in params.items():
                        control_data[key] = value
                
                # Write back to file
                with open(BOT_CONTROL_FILE, 'w') as f:
                    json.dump(control_data, f, indent=4)
                    
                # Update local values
                if running is not None:
                    self.bot_running = running
                if simulation_mode is not None:
                    self.simulation_mode = simulation_mode
                if params:
                    for key, value in params.items():
                        self.trading_params[key] = value
                        
                return True
            except Exception as e:
                logger.error(f"Error updating bot control: {e}")
                return False
        return False

class DashboardApp:
    """Dashboard application for Solana Trading Bot"""
    
    def __init__(self, data, port=DASHBOARD_PORT):
        """Initialize dashboard application"""
        self.data = data
        self.port = port
        
        # Check if Dash is available
        if not HAS_DASH:
            logger.error("Dash not available, cannot create dashboard")
            return
            
        # Initialize Flask server
        server = Flask(__name__)
        
        # Initialize Dash app
        self.app = dash.Dash(
            __name__,
            server=server,
            external_stylesheets=[dbc.themes.DARKLY],
            suppress_callback_exceptions=True
        )
        
        # Set app title
        self.app.title = "Solana Trading Bot Dashboard"
        
        # Create layout
        self.create_layout()
        
        # Register callbacks
        self.register_callbacks()
        
    def create_layout(self):
        """Create dashboard layout"""
        # Header section with title and status
        header = dbc.Row([
            dbc.Col(html.H1("Solana Trading Bot Dashboard"), width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Span("Bot Status: ", className="font-weight-bold"),
                            html.Span(id="bot-status", children="Loading...")
                        ], className="d-flex justify-content-between"),
                        html.Div([
                            html.Span("Mode: ", className="font-weight-bold"),
                            html.Span(id="bot-mode", children="Loading...")
                        ], className="d-flex justify-content-between mt-2"),
                        html.Div([
                            html.Button("Start Bot", id="start-bot-button", className="btn btn-success mt-2 me-2"),
                            html.Button("Stop Bot", id="stop-bot-button", className="btn btn-danger mt-2"),
                        ], className="d-flex justify-content-between mt-2"),
                    ])
                ], color="dark", outline=True)
            ], width=4)
        ], className="mb-4")
        
        # Wallet section showing balance and address
        wallet_section = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Wallet Info"),
                    dbc.CardBody([
                        html.Div([
                            html.Span("Address: ", className="font-weight-bold"),
                            html.Span(id="wallet-address", children="Loading...")
                        ], className="d-flex justify-content-between"),
                        html.Div([
                            html.Span("Balance: ", className="font-weight-bold"),
                            html.Span(id="wallet-balance", children="Loading...")
                        ], className="d-flex justify-content-between mt-2"),
                        html.Div([
                            html.Span("SOL Price: ", className="font-weight-bold"),
                            html.Span(id="sol-price", children="Loading...")
                        ], className="d-flex justify-content-between mt-2"),
                    ])
                ], color="dark", outline=True)
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Trading Summary"),
                    dbc.CardBody([
                        html.Div([
                            html.Span("P&L: ", className="font-weight-bold"),
                            html.Span(id="profit-loss", children="Loading...")
                        ], className="d-flex justify-content-between"),
                        html.Div([
                            html.Span("Trades Today: ", className="font-weight-bold"),
                            html.Span(id="trades-today", children="Loading...")
                        ], className="d-flex justify-content-between mt-2"),
                        html.Div([
                            html.Span("Successful / Failed: ", className="font-weight-bold"),
                            html.Span(id="trade-success-rate", children="Loading...")
                        ], className="d-flex justify-content-between mt-2"),
                    ])
                ], color="dark", outline=True)
            ], width=6)
        ], className="mb-4")
        
        # Trading parameters card
        parameters_card = dbc.Card([
            dbc.CardHeader("Trading Parameters"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Span("Initial Investment: ", className="font-weight-bold"),
                            html.Span(id="initial-investment", children="Loading...")
                        ], className="d-flex justify-content-between mb-2"),
                        html.Div([
                            html.Span("Max Investment: ", className="font-weight-bold"),
                            html.Span(id="max-investment", children="Loading...")
                        ], className="d-flex justify-content-between mb-2"),
                        html.Div([
                            html.Span("Min Liquidity: ", className="font-weight-bold"),
                            html.Span(id="min-liquidity", children="Loading...")
                        ], className="d-flex justify-content-between mb-2"),
                        html.Div([
                            html.Span("Min Price Change: ", className="font-weight-bold"),
                            html.Span(id="min-price-change", children="Loading...")
                        ], className="d-flex justify-content-between mb-2"),
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            html.Span("Take Profit: ", className="font-weight-bold"),
                            html.Span(id="take-profit", children="Loading...")
                        ], className="d-flex justify-content-between mb-2"),
                        html.Div([
                            html.Span("Stop Loss: ", className="font-weight-bold"),
                            html.Span(id="stop-loss", children="Loading...")
                        ], className="d-flex justify-content-between mb-2"),
                        html.Div([
                            html.Span("Trailing Stop: ", className="font-weight-bold"),
                            html.Span(id="trailing-stop", children="Loading...")
                        ], className="d-flex justify-content-between mb-2"),
                        html.Div([
                            html.Span("Max Slippage: ", className="font-weight-bold"),
                            html.Span(id="max-slippage", children="Loading...")
                        ], className="d-flex justify-content-between mb-2"),
                    ], width=6)
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Button(
                            "Edit Parameters",
                            id="edit-params-button",
                            className="btn btn-primary mt-2"
                        )
                    ], width=12, className="text-center")
                ])
            ])
        ], color="dark", outline=True, className="mb-4")
        
        # Balance history chart
        balance_chart = dbc.Card([
            dbc.CardHeader("Wallet Balance History"),
            dbc.CardBody([
                dcc.Graph(id="balance-chart")
            ])
        ], color="dark", outline=True, className="mb-4")
        
        # Tabs for active positions, recent trades, and logs
        tabs = dbc.Tabs([
            dbc.Tab([
                html.Div(id="active-positions-container", children=[
                    html.P("No active positions", className="text-center mt-3")
                ])
            ], label="Active Positions", className="mt-3"),
            dbc.Tab([
                html.Div(id="recent-trades-container", children=[
                    html.P("No recent trades", className="text-center mt-3")
                ])
            ], label="Recent Trades", className="mt-3"),
            dbc.Tab([
                html.Div(id="logs-container", children=[
                    html.P("No logs available", className="text-center mt-3")
                ])
            ], label="Logs", className="mt-3")
        ], className="mb-4")
        
        # Footer with uptime and version
        footer = dbc.Row([
            dbc.Col([
                html.Div([
                    html.Span("Uptime: ", className="font-weight-bold"),
                    html.Span(id="uptime", children="Loading...")
                ], className="d-flex justify-content-start"),
            ], width=6),
            dbc.Col([
                html.Div([
                    html.Span("Last Updated: ", className="font-weight-bold"),
                    html.Span(id="last-updated", children="Loading...")
                ], className="d-flex justify-content-end"),
            ], width=6)
        ], className="mt-4 mb-2")
        
        # Edit parameters modal
        edit_params_modal = dbc.Modal([
            dbc.ModalHeader("Edit Trading Parameters"),
            dbc.ModalBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Initial Investment (SOL)"),
                        dbc.Input(id="input-initial-investment", type="number", placeholder="0.05"),
                        dbc.Label("Max Investment (SOL)", className="mt-3"),
                        dbc.Input(id="input-max-investment", type="number", placeholder="0.1"),
                        dbc.Label("Min Liquidity (USD)", className="mt-3"),
                        dbc.Input(id="input-min-liquidity", type="number", placeholder="50000"),
                        dbc.Label("Min Price Change (%)", className="mt-3"),
                        dbc.Input(id="input-min-price-change", type="number", placeholder="3.0"),
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Take Profit (%)"),
                        dbc.Input(id="input-take-profit", type="number", placeholder="15.0"),
                        dbc.Label("Stop Loss (%)", className="mt-3"),
                        dbc.Input(id="input-stop-loss", type="number", placeholder="-7.5"),
                        dbc.Label("Trailing Stop (%)", className="mt-3"),
                        dbc.Input(id="input-trailing-stop", type="number", placeholder="5.0"),
                        dbc.Label("Max Slippage (%)", className="mt-3"),
                        dbc.Input(id="input-max-slippage", type="number", placeholder="2.5"),
                    ], width=6)
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Switch(
                            id="input-simulation-mode",
                            label="Simulation Mode",
                            value=True,
                            className="mt-3"
                        ),
                    ], width=12)
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Close", id="close-params-modal", className="ms-auto"),
                dbc.Button("Save", id="save-params", color="primary")
            ])
        ], id="edit-params-modal", size="lg")
        
        # Interval component for refreshing data
        interval = dcc.Interval(
            id='interval-component',
            interval=REFRESH_INTERVAL,  # in milliseconds
            n_intervals=0
        )
        
        # Put everything together
        self.app.layout = dbc.Container([
            header,
            wallet_section,
            balance_chart,
            parameters_card,
            tabs,
            footer,
            edit_params_modal,
            interval,
            # Store component for data
            dcc.Store(id='dashboard-data')
        ], fluid=True, className="p-4")
    
    def register_callbacks(self):
        """Register dashboard callbacks"""
        # Callback to update data periodically
        @self.app.callback(
            Output('dashboard-data', 'data'),
            Input('interval-component', 'n_intervals')
        )
        def update_data(n):
            self.data.reload_data()
            return {
                'wallet_address': self.data.wallet_address,
                'wallet_balance_sol': self.data.wallet_balance_sol,
                'wallet_balance_usd': self.data.wallet_balance_usd,
                'sol_price': self.data.sol_price,
                'bot_running': self.data.bot_running,
                'simulation_mode': self.data.simulation_mode,
                'trading_params': self.data.trading_params,
                'profit_loss': self.data.profit_loss,
                'trades_today': self.data.trades_today,
                'successful_trades': self.data.successful_trades,
                'failed_trades': self.data.failed_trades,
                'uptime': self.data.uptime,
                'balance_history': self.data.balance_history,
                'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Callback to update UI elements
        @self.app.callback(
            [
                Output('bot-status', 'children'),
                Output('bot-status', 'className'),
                Output('bot-mode', 'children'),
                Output('bot-mode', 'className'),
                Output('wallet-address', 'children'),
                Output('wallet-balance', 'children'),
                Output('sol-price', 'children'),
                Output('profit-loss', 'children'),
                Output('profit-loss', 'className'),
                Output('trades-today', 'children'),
                Output('trade-success-rate', 'children'),
                Output('initial-investment', 'children'),
                Output('max-investment', 'children'),
                Output('min-liquidity', 'children'),
                Output('min-price-change', 'children'),
                Output('take-profit', 'children'),
                Output('stop-loss', 'children'),
                Output('trailing-stop', 'children'),
                Output('max-slippage', 'children'),
                Output('uptime', 'children'),
                Output('last-updated', 'children'),
                Output('balance-chart', 'figure')
            ],
            Input('dashboard-data', 'data')
        )
        def update_ui(data):
            if not data:
                return ['Loading...'] * 21 + [{}]
                
            # Format wallet address for display (first 6 and last 4 chars)
            wallet_address = data['wallet_address']
            if wallet_address and len(wallet_address) > 10:
                display_address = f"{wallet_address[:6]}...{wallet_address[-4:]}"
            else:
                display_address = wallet_address or "Not connected"
                
            # Format balance
            balance_sol = data['wallet_balance_sol']
            balance_usd = data['wallet_balance_usd']
            if isinstance(balance_sol, dict) and 'sol' in balance_sol:
                balance_sol = balance_sol['sol']
                balance_usd = balance_sol['usd']
            balance_display = f"{balance_sol:.4f} SOL (${balance_usd:.2f})"
            
            # Format SOL price
            sol_price = data['sol_price']
            sol_price_display = f"${sol_price:.2f}"
            
            # Format bot status
            bot_running = data['bot_running']
            bot_status = "RUNNING" if bot_running else "STOPPED"
            bot_status_class = "text-success" if bot_running else "text-danger"
            
            # Format bot mode
            simulation_mode = data['simulation_mode']
            bot_mode = "SIMULATION" if simulation_mode else "REAL TRADING"
            bot_mode_class = "text-warning" if simulation_mode else "text-primary"
            
            # Format profit/loss
            profit_loss = data['profit_loss']
            if isinstance(profit_loss, dict):
                pl_sol = profit_loss.get('sol', 0)
                pl_usd = profit_loss.get('usd', 0)
                pl_display = f"{pl_sol:.4f} SOL (${pl_usd:.2f})"
                pl_class = "text-success" if pl_sol > 0 else "text-danger" if pl_sol < 0 else ""
            else:
                pl_display = "N/A"
                pl_class = ""
                
            # Format trades today
            trades_today = data['trades_today']
            trades_today_display = str(trades_today)
            
            # Format success rate
            successful_trades = data['successful_trades']
            failed_trades = data['failed_trades']
            success_rate_display = f"{successful_trades} / {failed_trades}"
            
            # Format trading parameters
            trading_params = data['trading_params']
            initial_investment = trading_params.get('initial_investment_sol', 'N/A')
            max_investment = trading_params.get('max_investment_per_token_sol', 'N/A')
            min_liquidity = trading_params.get('min_liquidity_usd', 'N/A')
            min_price_change = trading_params.get('min_price_change_percent', 'N/A')
            take_profit = trading_params.get('take_profit_percent', 'N/A')
            stop_loss = trading_params.get('stop_loss_percent', 'N/A')
            trailing_stop = trading_params.get('trailing_stop_percent', 'N/A')
            max_slippage = trading_params.get('max_slippage_percent', 'N/A')
            
            # Format initial investment
            if initial_investment != 'N/A':
                initial_investment = f"{initial_investment} SOL"
                
            # Format max investment
            if max_investment != 'N/A':
                max_investment = f"{max_investment} SOL"
                
            # Format min liquidity
            if min_liquidity != 'N/A':
                min_liquidity = f"${min_liquidity}"
                
            # Format min price change
            if min_price_change != 'N/A':
                min_price_change = f"{min_price_change}%"
                
            # Format take profit
            if take_profit != 'N/A':
                take_profit = f"{take_profit}%"
                
            # Format stop loss
            if stop_loss != 'N/A':
                stop_loss = f"{stop_loss}%"
                
            # Format trailing stop
            if trailing_stop != 'N/A':
                trailing_stop = f"{trailing_stop}%"
                
            # Format max slippage
            if max_slippage != 'N/A':
                max_slippage = f"{max_slippage}%"
                
            # Format uptime
            uptime = data['uptime']
            hours, remainder = divmod(uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_display = f"{hours}h {minutes}m {seconds}s"
            
            # Format last updated
            last_updated = data['last_updated']
            
            # Create balance chart
            fig = self.create_balance_chart(data['balance_history'])
            
            return [
                bot_status, bot_status_class,
                bot_mode, bot_mode_class,
                display_address,
                balance_display,
                sol_price_display,
                pl_display, pl_class,
                trades_today_display,
                success_rate_display,
                initial_investment,
                max_investment,
                min_liquidity,
                min_price_change,
                take_profit,
                stop_loss,
                trailing_stop,
                max_slippage,
                uptime_display,
                last_updated,
                fig
            ]
        
        # Callback to handle bot start
        @self.app.callback(
            Output('start-bot-button', 'disabled'),
            Input('start-bot-button', 'n_clicks'),
            State('dashboard-data', 'data'),
            prevent_initial_call=True
        )
        def start_bot(n_clicks, data):
            if n_clicks:
                result = self.data.update_bot_control(running=True)
                return not result
            return False
        
        # Callback to handle bot stop
        @self.app.callback(
            Output('stop-bot-button', 'disabled'),
            Input('stop-bot-button', 'n_clicks'),
            State('dashboard-data', 'data'),
            prevent_initial_call=True
        )
        def stop_bot(n_clicks, data):
            if n_clicks:
                result = self.data.update_bot_control(running=False)
                return not result
            return False
        
        # Callback to open edit parameters modal
        @self.app.callback(
            [
                Output('edit-params-modal', 'is_open'),
                Output('input-initial-investment', 'value'),
                Output('input-max-investment', 'value'),
                Output('input-min-liquidity', 'value'),
                Output('input-min-price-change', 'value'),
                Output('input-take-profit', 'value'),
                Output('input-stop-loss', 'value'),
                Output('input-trailing-stop', 'value'),
                Output('input-max-slippage', 'value'),
                Output('input-simulation-mode', 'value')
            ],
            [
                Input('edit-params-button', 'n_clicks'),
                Input('close-params-modal', 'n_clicks'),
                Input('save-params', 'n_clicks')
            ],
            [
                State('edit-params-modal', 'is_open'),
                State('dashboard-data', 'data'),
                State('input-initial-investment', 'value'),
                State('input-max-investment', 'value'),
                State('input-min-liquidity', 'value'),
                State('input-min-price-change', 'value'),
                State('input-take-profit', 'value'),
                State('input-stop-loss', 'value'),
                State('input-trailing-stop', 'value'),
                State('input-max-slippage', 'value'),
                State('input-simulation-mode', 'value')
            ],
            prevent_initial_call=True
        )
        def toggle_edit_params_modal(edit_clicks, close_clicks, save_clicks, 
                                     is_open, data, init_inv, max_inv, min_liq, 
                                     min_price, take_profit, stop_loss, 
                                     trailing_stop, max_slip, sim_mode):
            ctx = dash.callback_context
            if not ctx.triggered:
                raise dash.exceptions.PreventUpdate
                
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            if trigger_id == 'edit-params-button' and not is_open:
                # Opening the modal, populate with current values
                trading_params = data['trading_params']
                return [
                    True,  # Open modal
                    trading_params.get('initial_investment_sol', 0.05),
                    trading_params.get('max_investment_per_token_sol', 0.1),
                    trading_params.get('min_liquidity_usd', 50000),
                    trading_params.get('min_price_change_percent', 3.0),
                    trading_params.get('take_profit_percent', 15.0),
                    trading_params.get('stop_loss_percent', -7.5),
                    trading_params.get('trailing_stop_percent', 5.0),
                    trading_params.get('max_slippage_percent', 2.5),
                    data['simulation_mode']
                ]
            elif trigger_id == 'save-params' and is_open:
                # Save parameters
                params = {
                    'initial_investment_sol': init_inv,
                    'max_investment_per_token_sol': max_inv,
                    'min_liquidity_usd': min_liq,
                    'min_price_change_percent': min_price,
                    'take_profit_percent': take_profit,
                    'stop_loss_percent': stop_loss,
                    'trailing_stop_percent': trailing_stop,
                    'max_slippage_percent': max_slip
                }
                self.data.update_bot_control(
                    simulation_mode=sim_mode,
                    params=params
                )
                return [False] + [dash.no_update] * 9
            elif trigger_id == 'close-params-modal' and is_open:
                # Just close the modal
                return [False] + [dash.no_update] * 9
            
            raise dash.exceptions.PreventUpdate
        
        # Callback to update active positions
        @self.app.callback(
            Output('active-positions-container', 'children'),
            Input('interval-component', 'n_intervals')
        )
        def update_active_positions(n):
            positions = self.data.active_positions
            if not positions:
                return html.P("No active positions", className="text-center mt-3")
                
            # Create a table of active positions
            table_header = [
                html.Thead(html.Tr([
                    html.Th("Token"),
                    html.Th("Amount"),
                    html.Th("Entry Price"),
                    html.Th("Current Price"),
                    html.Th("P&L"),
                    html.Th("Action")
                ]))
            ]
            
            rows = []
            for position in positions:
                token_name = position.get('ticker', 'Unknown')
                amount = position.get('amount', 0)
                entry_price = position.get('buy_price', 0)
                current_price = position.get('current_price_usd', 0)
                pl_pct = position.get('profit_loss_pct', 0)
                
                # Format P&L with color
                if pl_pct > 0:
                    pl_display = html.Span(f"+{pl_pct:.2f}%", className="text-success")
                elif pl_pct < 0:
                    pl_display = html.Span(f"{pl_pct:.2f}%", className="text-danger")
                else:
                    pl_display = html.Span(f"{pl_pct:.2f}%")
                    
                # Add row
                rows.append(html.Tr([
                    html.Td(token_name),
                    html.Td(f"{amount:.4f}"),
                    html.Td(f"${entry_price:.8f}"),
                    html.Td(f"${current_price:.8f}"),
                    html.Td(pl_display),
                    html.Td(html.Button("Sell", className="btn btn-sm btn-danger"))
                ]))
                
            table_body = [html.Tbody(rows)]
            
            return dbc.Table(
                table_header + table_body,
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                className="mt-3"
            )
        
        # Callback to update recent trades
        @self.app.callback(
            Output('recent-trades-container', 'children'),
            Input('interval-component', 'n_intervals')
        )
        def update_recent_trades(n):
            trades = self.data.recent_trades
            if not trades:
                return html.P("No recent trades", className="text-center mt-3")
                
            # Create a table of recent trades
            table_header = [
                html.Thead(html.Tr([
                    html.Th("Time"),
                    html.Th("Token"),
                    html.Th("Action"),
                    html.Th("Amount"),
                    html.Th("Price"),
                    html.Th("P&L")
                ]))
            ]
            
            rows = []
            for trade in trades:
                # Format timestamp
                timestamp = trade.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.datetime.fromisoformat(timestamp)
                        timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                        
                token_address = trade.get('contract_address', '')
                token_name = trade.get('ticker', token_address[:8] if token_address else 'Unknown')
                action = trade.get('action', 'UNKNOWN')
                amount = trade.get('amount', 0)
                price = trade.get('price', 0)
                pl = trade.get('gain_loss_sol', 0)
                
                # Format P&L with color
                if action == 'SELL':
                    if pl > 0:
                        pl_display = html.Span(f"+{pl:.4f} SOL", className="text-success")
                    elif pl < 0:
                        pl_display = html.Span(f"{pl:.4f} SOL", className="text-danger")
                    else:
                        pl_display = html.Span(f"{pl:.4f} SOL")
                else:
                    pl_display = ""
                    
                # Format action with color
                if action == 'BUY':
                    action_display = html.Span(action, className="text-primary")
                elif action == 'SELL':
                    action_display = html.Span(action, className="text-danger")
                else:
                    action_display = html.Span(action)
                    
                # Add row
                rows.append(html.Tr([
                    html.Td(timestamp),
                    html.Td(token_name),
                    html.Td(action_display),
                    html.Td(f"{amount:.4f}"),
                    html.Td(f"${price:.8f}"),
                    html.Td(pl_display)
                ]))
                
            table_body = [html.Tbody(rows)]
            
            return dbc.Table(
                table_header + table_body,
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                className="mt-3"
            )
        
        # Callback to update logs
        @self.app.callback(
            Output('logs-container', 'children'),
            Input('interval-component', 'n_intervals')
        )
        def update_logs(n):
            logs = self.data.recent_logs
            if not logs:
                return html.P("No logs available", className="text-center mt-3")
                
            # Create a log display
            log_items = []
            for log in logs:
                # Determine log level and apply styling
                if ' - ERROR - ' in log:
                    log_class = "text-danger"
                elif ' - WARNING - ' in log:
                    log_class = "text-warning"
                elif ' - INFO - ' in log:
                    log_class = "text-info"
                else:
                    log_class = ""
                    
                log_items.append(html.P(log, className=log_class))
                
            return html.Div([
                html.Div(
                    log_items,
                    style={
                        'maxHeight': '500px',
                        'overflowY': 'auto',
                        'fontFamily': 'monospace',
                        'fontSize': '12px',
                        'whiteSpace': 'pre-wrap',
                        'padding': '10px',
                        'backgroundColor': '#222',
                        'border': '1px solid #333',
                        'borderRadius': '5px'
                    }
                )
            ], className="mt-3")
    
    def create_balance_chart(self, history):
        """Create balance history chart"""
        # Default empty chart
        if not history:
            return go.Figure(
                layout=dict(
                    title="Wallet Balance History",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="Balance (SOL)"),
                    template="plotly_dark"
                )
            )
            
        # Convert to dataframe if pandas is available
        if HAS_PANDAS:
            df = pd.DataFrame(history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create figure with two y-axes
            fig = go.Figure()
            
            # Add SOL balance line
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['sol'],
                name="SOL Balance",
                line=dict(color='yellow', width=2)
            ))
            
            # Add USD balance line
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['usd'],
                name="USD Value",
                line=dict(color='green', width=2),
                yaxis="y2"
            ))
            
            # Update layout
            fig.update_layout(
                title="Wallet Balance History",
                xaxis=dict(title="Time"),
                yaxis=dict(title="Balance (SOL)", titlefont=dict(color="yellow")),
                yaxis2=dict(
                    title="Value (USD)",
                    titlefont=dict(color="green"),
                    anchor="x",
                    overlaying="y",
                    side="right"
                ),
                template="plotly_dark",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            return fig
        else:
            # Basic figure without pandas
            timestamps = [h.get('timestamp', '') for h in history]
            sol_values = [h.get('sol', 0) for h in history]
            
            return go.Figure(
                data=[
                    go.Scatter(
                        x=timestamps,
                        y=sol_values,
                        mode="lines",
                        name="SOL Balance",
                        line=dict(color='yellow', width=2)
                    )
                ],
                layout=dict(
                    title="Wallet Balance History",
                    xaxis=dict(title="Time"),
                    yaxis=dict(title="Balance (SOL)"),
                    template="plotly_dark"
                )
            )
    
    def run(self):
        """Run the dashboard app"""
        if hasattr(self, 'app'):
            self.app.run_server(debug=False, host='0.0.0.0', port=self.port)
        else:
            logger.error("Dashboard app not initialized")

def main():
    """Main function to run the dashboard"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Solana Trading Bot Dashboard")
    parser.add_argument("--port", type=int, default=DASHBOARD_PORT, help="Dashboard port")
    args = parser.parse_args()
    
    # Check if Dash is available
    if not HAS_DASH:
        print("Dash is not installed. Please install it with:")
        print("pip install dash dash-bootstrap-components plotly")
        return
        
    # Create dashboard data
    data = DashboardData()
    
    # Create dashboard app
    app = DashboardApp(data, port=args.port)
    
    # Run dashboard
    app.run()

if __name__ == "__main__":
    main()
