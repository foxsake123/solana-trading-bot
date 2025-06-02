#!/usr/bin/env python3
"""
Test script to verify simulation mode is using real tokens
"""

import asyncio
import logging
import json
import os
from datetime import datetime

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_real_tokens')

async def test_token_scanner():
    """Test if token scanner returns real tokens"""
    try:
        # Import necessary modules
        from core.birdeye import BirdeyeAPI
        from token_scanner import TokenScanner
        from database import Database
        
        logger.info("=== Testing Token Scanner ===")
        
        # Initialize components
        db = Database(db_path='data/test_real_tokens.db')
        birdeye_api = BirdeyeAPI()
        
        # Create token scanner with BirdeyeAPI
        scanner = TokenScanner(db=db, birdeye_api=birdeye_api)
        
        # Test 1: Get top gainers
        logger.info("\nTest 1: Fetching top gainers...")
        top_gainers = await scanner.get_top_gainers()
        
        if top_gainers:
            logger.info(f"✅ Found {len(top_gainers)} top gainers")
            for i, token in enumerate(top_gainers[:3]):  # Show first 3
                address = token.get('contract_address', '')
                ticker = token.get('ticker', 'UNKNOWN')
                price = token.get('price_usd', 0)
                
                # Check if it's a real token (not Sim*)
                is_real = not address.startswith('Sim')
                status = "✅ REAL" if is_real else "❌ FAKE"
                
                logger.info(f"  {i+1}. {ticker} - {address[:16]}... - ${price:.8f} - {status}")
        else:
            logger.warning("❌ No top gainers found")
        
        # Test 2: Get trending tokens
        logger.info("\nTest 2: Fetching trending tokens...")
        trending = await scanner.get_trending_tokens()
        
        if trending:
            logger.info(f"✅ Found {len(trending)} trending tokens")
            for i, token in enumerate(trending[:3]):  # Show first 3
                address = token.get('contract_address', '')
                ticker = token.get('ticker', 'UNKNOWN')
                volume = token.get('volume_24h', 0)
                
                is_real = not address.startswith('Sim')
                status = "✅ REAL" if is_real else "❌ FAKE"
                
                logger.info(f"  {i+1}. {ticker} - Volume: ${volume:,.2f} - {status}")
        else:
            logger.warning("❌ No trending tokens found")
        
        return top_gainers, trending
        
    except Exception as e:
        logger.error(f"Error testing token scanner: {e}")
        import traceback
        traceback.print_exc()
        return [], []

async def test_token_analyzer():
    """Test if token analyzer uses real data"""
    try:
        from core.birdeye import BirdeyeAPI
        from token_analyzer import TokenAnalyzer
        from database import Database
        
        logger.info("\n=== Testing Token Analyzer ===")
        
        # Initialize components
        db = Database(db_path='data/test_real_tokens.db')
        birdeye_api = BirdeyeAPI()
        
        # Create token analyzer
        analyzer = TokenAnalyzer(db=db, birdeye_api=birdeye_api)
        
        # Test with a known real token (e.g., a popular meme coin)
        # You can replace this with any real Solana token address
        test_addresses = [
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Bonk
            "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",  # PopCat
        ]
        
        for address in test_addresses:
            logger.info(f"\nAnalyzing token: {address}")
            
            # Fetch token data
            token_data = await analyzer.fetch_token_data(address)
            
            if token_data:
                ticker = token_data.get('ticker', 'UNKNOWN')
                price = token_data.get('price_usd', 0)
                liquidity = token_data.get('liquidity_usd', 0)
                
                logger.info(f"  Ticker: {ticker}")
                logger.info(f"  Price: ${price:.8f}")
                logger.info(f"  Liquidity: ${liquidity:,.2f}")
                
                # Get safety score
                safety_score = await analyzer.get_safety_score(address)
                logger.info(f"  Safety Score: {safety_score:.1f}/100")
                
                # Full analysis
                analysis = await analyzer.analyze_token(address)
                recommendation = "BUY" if analysis['buy_recommendation'] else "NO BUY"
                logger.info(f"  Recommendation: {recommendation}")
                
                if analysis.get('reasons'):
                    logger.info("  Reasons:")
                    for reason in analysis['reasons']:
                        logger.info(f"    - {reason}")
            else:
                logger.warning(f"❌ No data found for {address}")
                
    except Exception as e:
        logger.error(f"Error testing token analyzer: {e}")
        import traceback
        traceback.print_exc()

async def test_real_trading_simulation():
    """Test a simulated trade with real token"""
    try:
        from core.simplified_solana_trader import SolanaTrader
        from core.database import Database
        from core.database_adapter import DatabaseAdapter
        
        logger.info("\n=== Testing Simulated Trading ===")
        
        # Initialize trader in simulation mode
        db = Database(db_path='data/test_real_tokens.db')
        db_adapter = DatabaseAdapter(db)
        
        trader = SolanaTrader(db=db_adapter, simulation_mode=True)
        await trader.connect()
        
        # Get wallet balance
        balance_sol, balance_usd = await trader.get_wallet_balance()
        logger.info(f"Simulation wallet balance: {balance_sol:.4f} SOL (${balance_usd:.2f})")
        
        # Test trade with a real token address
        test_token = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # Bonk
        amount = 0.01  # 0.01 SOL
        
        logger.info(f"\nSimulating BUY of {amount} SOL worth of {test_token}")
        
        # Execute simulated trade
        tx_hash = await trader.buy_token(test_token, amount)
        
        # Check transaction hash
        if tx_hash.startswith("SIM_"):
            logger.info(f"✅ Simulated trade executed: {tx_hash}")
        else:
            logger.warning(f"❌ Unexpected transaction format: {tx_hash}")
        
        # Check database for the trade
        trades = db.get_trade_history(limit=1)
        if trades:
            latest_trade = trades[0]
            logger.info(f"\nLatest trade in database:")
            logger.info(f"  Token: {latest_trade['contract_address']}")
            logger.info(f"  Action: {latest_trade['action']}")
            logger.info(f"  Amount: {latest_trade['amount']} SOL")
            logger.info(f"  Is Real Token: {not latest_trade['contract_address'].startswith('Sim')}")
        
        await trader.close()
        
    except Exception as e:
        logger.error(f"Error testing trading simulation: {e}")
        import traceback
        traceback.print_exc()

def check_bot_settings():
    """Check bot control settings"""
    logger.info("\n=== Checking Bot Settings ===")
    
    control_file = "bot_control.json"
    if not os.path.exists(control_file):
        control_file = "data/bot_control.json"
    
    if os.path.exists(control_file):
        with open(control_file, 'r') as f:
            settings = json.load(f)
        
        logger.info(f"Simulation Mode: {settings.get('simulation_mode', True)}")
        logger.info(f"Use BirdEye API: {settings.get('use_birdeye_api', False)}")
        logger.info(f"Use Machine Learning: {settings.get('use_machine_learning', False)}")
        
        if not settings.get('use_birdeye_api', False):
            logger.warning("⚠️  BirdEye API is disabled! Enable it to fetch real tokens.")
    else:
        logger.error("❌ bot_control.json not found!")

async def main():
    """Run all tests"""
    print("🧪 Testing Real Tokens in Simulation Mode")
    print("=" * 60)
    
    # Check settings first
    check_bot_settings()
    
    # Test token scanner
    top_gainers, trending = await test_token_scanner()
    
    # Test token analyzer
    await test_token_analyzer()
    
    # Test simulated trading
    await test_real_trading_simulation()
    
    print("\n" + "=" * 60)
    print("✅ Testing complete! Check the output above for results.")
    
    # Summary
    print("\n📋 Summary:")
    if top_gainers:
        real_tokens = [t for t in top_gainers if not t.get('contract_address', '').startswith('Sim')]
        print(f"  - Token Scanner: {len(real_tokens)}/{len(top_gainers)} real tokens")
    else:
        print("  - Token Scanner: ❌ No tokens found")
    
    print("\n💡 What to look for:")
    print("  - Token addresses should NOT start with 'Sim'")
    print("  - Prices should be realistic (not random)")
    print("  - Liquidity and volume should vary (not fixed values)")
    print("  - All tokens should have real Solana addresses")

if __name__ == "__main__":
    asyncio.run(main())