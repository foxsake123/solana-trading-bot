# Solana Trading Bot - Running Instructions

This document provides detailed instructions for running the Solana Trading Bot and its dashboard.

## Setup Overview

1. **Directory Structure**: Everything should be in `C:\Users\shorg\sol-bot_claude`
2. **Environment**: Python virtual environment with required dependencies
3. **Bot Mode**: By default, the bot runs in simulation mode (no real trades)

## Important Files

- `main.py`: The main bot process
- `dashboard.py`: Web interface for monitoring and controlling the bot
- `.env`: Configuration for API keys and trading parameters
- `data/bot_control.json`: Runtime control settings

## Running the Bot

### 1. Start the Main Bot Process

```bash
# Activate the virtual environment
cd C:\Users\shorg\sol-bot_claude
venv\Scripts\activate

# Run the main bot
python main.py
```

The bot will:
- Initialize the database
- Connect to your wallet
- Scan Twitter and DexScreener for tokens
- Analyze and trade tokens based on your criteria
- Monitor positions for take profit or stop loss events

### 2. Run the Dashboard (in a separate terminal)

```bash
# In a new terminal window
cd C:\Users\shorg\sol-bot_claude
venv\Scripts\activate

# Run the dashboard
streamlit run dashboard.py
```

This will open a browser window with the trading dashboard.

## Important Settings

### Simulation Mode

The bot is currently set to **simulation mode** (no real trades). To enable real trading:

1. Open `solana_trader.py`
2. Find the line: `self.simulation_mode = True`
3. Change it to: `self.simulation_mode = False`

**WARNING**: Only switch to real trading once you've tested thoroughly and understand the risks.

### Trading Parameters

You can adjust these settings in the dashboard or directly in `.env`:

- `TAKE_PROFIT_TARGET=1.5`: 50% profit target
- `STOP_LOSS_PERCENTAGE=0.25`: 25% stop loss
- `MAX_INVESTMENT_PER_TOKEN=0.10`: 0.1 SOL per token

## Troubleshooting

### Common Issues

1. **"Wallet private key not provided"**:
   - Make sure your `.env` file has `WALLET_PRIVATE_KEY=your_private_key_here`
   - Check that the file is saved as `.env` (not `.env.txt`)

2. **API Errors**:
   - DexScreener API: The code should automatically handle the endpoint fix
   - Jupiter API: The code now properly formats parameters

3. **Token Balance Errors**:
   - The error `'dict' object has no attribute 'encoding'` is fixed in the updated code

4. **No Trades in Phantom Wallet**:
   - This is normal in simulation mode. The bot is recording trades in its database but not executing them on-chain

### Logs

Check these locations for troubleshooting:
- Console output when running the bot
- Log files in the `logs` directory
- Database in `data/trading_bot.db`

## Security Notes

- Your wallet private key is stored in the `.env` file
- Use a dedicated wallet with limited funds for trading
- Start with small amounts until you're confident the system works as expected

## Next Steps

1. Test the bot in simulation mode
2. Use the dashboard to monitor performance
3. Only after thorough testing, consider enabling real trading by turning off simulation mode