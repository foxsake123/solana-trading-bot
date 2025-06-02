# start_bot_simulation.py
import asyncio
import logging
import os
import sys

# Add core to path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def start_bot():
    """Start the bot in simulation mode"""
    try:
        # Import the run_bot_updated module
        from run_bot_updated import run_bot
        
        print("\n🚀 Starting Solana Trading Bot in Simulation Mode...")
        print("=" * 60)
        print("📊 The bot will now:")
        print("  - Scan for trending tokens every 60 seconds")
        print("  - Analyze tokens for buy opportunities")
        print("  - Execute simulated trades")
        print("  - Monitor positions for take profit/stop loss")
        print("=" * 60)
        print("\nPress Ctrl+C to stop the bot\n")
        
        # Run the bot
        await run_bot()
        
    except KeyboardInterrupt:
        print("\n\n⛔ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(start_bot())