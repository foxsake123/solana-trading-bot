# Create a script named check_real_trades.py
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/sol_bot.db')
# List of your real token addresses
real_tokens = [
    '2gb5ywHn5UJKqrhhGKkNYgv3CZBDEakJsqhuUgeAnWHS',
    '4TQfk8K29fEFzpfoA6aZdBJdC2y7D2w5ZdYt5f1Rwyrf',
    '6t4pBC4Wbu38xkkEcELcZL85FLk32VuzjboYgf1fbonk',
    '8hhRHZkoCwLojdSthxu3Ho5K2j4BZHnSZ93HZjd4Mxo6',
    '9YLAtHLRRE6yDwogLvijuHXgZJtiHAU3ykGDx3rgbonk',
    'AtortPA9SVbkKmdzu5zg4jxgkR4howvPshorA9jYbonk',
    'GcCfPKRq2n5gJZQRBRyqKu7b382igWCg4qwhfF7twLiQ',
    'H4cwzkkLa8thnkdvfF7FCwcEteDyB9BRmjMgnNACTsGo'
]

# Query to find all trades for these tokens
query = f"""
SELECT * FROM trades 
WHERE contract_address IN ('{"','".join(real_tokens)}')
ORDER BY timestamp DESC
"""

trades = pd.read_sql(query, conn)
print("\n===== REAL TOKEN TRADES =====")
print(trades)

conn.close()
