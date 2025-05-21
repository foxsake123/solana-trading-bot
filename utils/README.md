# Solana Trading Bot

A trading bot for the Solana blockchain. This bot can automatically identify and trade tokens on Solana-based decentralized exchanges.

## Directory Structure

- `core/` - Core functionality (trading, token scanning, etc.)
- `data/` - Data storage (database, control settings)
- `dashboard/` - Monitoring dashboards
- `tests/` - Test scripts
- `utils/` - Utility scripts
- `logs/` - Log files

## Setup

1. Install the dependencies
2. Configure your environment variables
3. Run the bot

### Prerequisites

- Python 3.9+
- pip
- Git

### Installation

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the dependencies
pip install -r requirements.txt
```

### Configuration

1. Create a `.env` file in the root directory with the following variables:

```
WALLET_PRIVATE_KEY=your_private_key_here
SOLANA_RPC_ENDPOINT=https://api.mainnet-beta.solana.com
BIRDEYE_API_KEY=your_birdeye_api_key_here (optional)
TWITTER_API_KEY=your_twitter_api_key_here (optional)
TWITTER_API_SECRET=your_twitter_api_secret_here (optional)
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here (optional)
```

2. Edit the `bot_control.json` file to configure the bot's behavior:

```json
{
    "running": false,
    "simulation_mode": true,
    "filter_fake_tokens": true,
    "use_birdeye_api": true,
    "use_machine_learning": false,
    "take_profit_target": 15.0,
    "stop_loss_percentage": 0.25,
    "max_investment_per_token": 0.1,
    "min_investment_per_token": 0.02,
    "slippage_tolerance": 0.3,
    "MIN_SAFETY_SCORE": 0.0,
    "MIN_VOLUME": 0.0,
    "MIN_LIQUIDITY": 0.0,
    "MIN_MCAP": 0.0,
    "MIN_HOLDERS": 0,
    "MIN_PRICE_CHANGE_1H": 0.0,
    "MIN_PRICE_CHANGE_6H": 0.0,
    "MIN_PRICE_CHANGE_24H": 0.0
}
```

### Testing

Before running the bot in real mode, you should test it thoroughly:

```bash
# Test real trading functionality
python tests/test_real_trading.py

# Check current trades and positions
python tests/check_trades.py

# Setup real trading mode
python utils/setup_real_trading.py

# Monitor the bot with a dashboard
python dashboard/new_dashboard.py
```

### Running the Bot

To start the bot:

1. Set `"running": true` in `bot_control.json`
2. For real trading, set `"simulation_mode": false` in `bot_control.json`
3. Run the main script:

```bash
python main.py
```

## Disclaimer

This is experimental software. Use at your own risk. Never invest more than you can afford to lose.

When running in real trading mode, the bot will use real SOL tokens from your wallet. Always start with small amounts when testing.
