# fix_simplified_trading_bot.py
import os

def fix_trading_bot():
    """Update the trading bot to use real tokens instead of simulation ones"""
    
    # First, let's check what file we need to update
    files_to_check = [
        'simplified_trading_bot.py',
        'core/simplified_trading_bot.py',
        'trading_bot.py',
        'core/trading_bot.py'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for the simulation token generation
            if 'SIM: Bought' in content or 'buy_token("SIM' in content:
                print(f"Found simulation token code in {file_path}")
                
                # Replace simulation token logic
                # Find and replace the part that buys SIM tokens
                if 'for i in range(3):' in content and 'buy_token(f"SIM{i}"' in content:
                    # Replace with code that uses real tokens
                    old_code = '''for i in range(3):
            if self.balance >= 0.5:
                await self.buy_token(f"SIM{i}", 0.5)'''
                    
                    new_code = '''# Get real tokens to trade
        if hasattr(self.token_scanner, 'birdeye_api') and self.token_scanner.birdeye_api:
            logger.info("Fetching real tokens to trade...")
            top_gainers = await self.token_scanner.get_top_gainers()
            trending = await self.token_scanner.get_trending_tokens()
            
            # Combine tokens
            all_tokens = top_gainers[:3] + trending[:2]  # Get top 3 gainers and 2 trending
            
            for token in all_tokens[:5]:  # Trade up to 5 tokens
                if self.balance >= self.config.get('max_investment_per_token', 0.1):
                    address = token.get('contract_address', token.get('address', ''))
                    if address and not address.startswith('SIM'):
                        # Analyze token before buying
                        if self.token_scanner.token_analyzer:
                            analysis = await self.token_scanner.token_analyzer.analyze_token(address)
                            if analysis.get('buy_recommendation', False):
                                amount = self.config.get('max_investment_per_token', 0.1)
                                logger.info(f"Buying {amount} SOL of {token.get('ticker', 'Unknown')} ({address[:8]}...)")
                                await self.buy_token(address, amount)
                        else:
                            # Buy without analysis
                            amount = self.config.get('max_investment_per_token', 0.1)
                            await self.buy_token(address, amount)'''
                    
                    content = content.replace(old_code, new_code)
                    
                    # Save the updated file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"✅ Updated {file_path} to use real tokens")
                    break

if __name__ == "__main__":
    fix_trading_bot()