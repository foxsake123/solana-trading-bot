# Solana Trading Bot

A bot for trading tokens on the Solana blockchain with real trading capabilities and simulation mode.

## Features

- **Real Trading**: Execute real trades on Solana DEXes via Jupiter Aggregator
- **Simulation Mode**: Practice trading strategies with real market data
- **Token Analysis**: Evaluate tokens based on liquidity, volume, and price action
- **Automated Trading**: Set take profit and stop loss levels
- **Position Monitoring**: Track active positions and execute sell strategies

## Directory Structure

- `main.py` - Main entry point
- `core/` - Core functionality
  - `solana_trader.py` - Trading logic
  - `token_scanner.py` - Token discovery
  - `token_analyzer.py` - Token analysis and scoring
  - `database.py` - Database operations
  - `solders_adapter.py` - Solana blockchain integration
  - `config.py` - Configuration settings
- `utils/` - Utility modules
- `data/` - Database and data files 
- `bot_control.json` - Bot control settings

## Quick Start

1. **Setup Environment**:
   ```bash
   # Create a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configuration**:
   - Copy `.env.example` to `.env` and add your wallet private key
   - Adjust settings in `bot_control.json`

3. **Start in Simulation Mode**:
   ```bash
   python main.py
   ```

4. **Monitor Activity**:
   ```bash
   python status_monitor.py
   ```

## Setting Up Real Trading

1. **Configure for Real Trading**:
   ```bash
   python setup_real_trading.py
   ```

2. **Test with Minimal Amount**:
   ```bash
   python test_real_trading.py
   ```

3. **Start Real Trading**:
   - Ensure `simulation_mode` is set to `false` in `bot_control.json`
   - Set `running` to `true` in `bot_control.json`
   - Run `python main.py`

## Monitoring Tools

- `status_monitor.py` - Real-time status monitor
- `check_trades.py` - View trades and positions
  - Use `-a` flag to include simulation trades
  - Use `-l 50` to show more entries

## Important Notes

- Always test with small amounts first
- Be aware of network fees and slippage
- Real trading involves financial risk
- Keep your private key secure

## Trading Parameters

Key parameters to configure in `bot_control.json`:

- `max_investment_per_token` - Maximum SOL per trade
- `take_profit_target` - Percentage gain to trigger sell
- `stop_loss_percentage` - Maximum loss before selling
- `MIN_LIQUIDITY` - Minimum token liquidity in USD
- `MIN_VOLUME` - Minimum 24h trading volume

## License

This project is licensed under the MIT License - see the LICENSE file for details.