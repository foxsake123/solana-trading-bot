"""
Calculate real P&L based on your wallet address
"""
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('real_pl')

def get_wallet_pl():
    """Calculate P&L for your real wallet"""
    
    # Your wallet address from the explorer link
    wallet_address = "16um9NG9V88CWR9vESe42WfmNrDcTNq9jUit5t5mpgf"
    
    # Get current balance
    current_balance_sol = 0.001452387  # From your explorer link
    
    # Starting balance
    starting_balance_sol = 2.0  # You mentioned starting with 2 SOL
    
    # Get current SOL price
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
            timeout=10
        )
        sol_price = 180.0  # Default
        if response.status_code == 200:
            data = response.json()
            sol_price = data['solana']['usd']
    except:
        sol_price = 180.0
    
    # Calculate P&L
    pl_sol = current_balance_sol - starting_balance_sol
    pl_percentage = (current_balance_sol / starting_balance_sol - 1) * 100
    pl_usd = pl_sol * sol_price
    
    # Display results
    print("\n" + "="*60)
    print("REAL WALLET P&L ANALYSIS")
    print("="*60)
    print(f"Wallet Address: {wallet_address}")
    print(f"Starting Balance: {starting_balance_sol:.6f} SOL (${starting_balance_sol * sol_price:.2f})")
    print(f"Current Balance: {current_balance_sol:.6f} SOL (${current_balance_sol * sol_price:.2f})")
    print(f"SOL Price: ${sol_price:.2f}")
    print("-"*60)
    print(f"Total P&L: {pl_sol:.6f} SOL (${pl_usd:.2f})")
    print(f"Percentage: {pl_percentage:.2f}%")
    print(f"Status: {'LOSS' if pl_sol < 0 else 'PROFIT'}")
    print("="*60)
    
    # Show what the bot_control.json should look like for real trading
    if pl_percentage < -90:
        print("\n⚠️  WARNING: Significant losses detected!")
        print("Recommendations:")
        print("1. Keep bot in SIMULATION mode until strategy is refined")
        print("2. Use tighter stop losses (5% instead of 25%)")
        print("3. Reduce position sizes")
        print("4. Enable the AI algorithm for better trade selection")

if __name__ == "__main__":
    get_wallet_pl()