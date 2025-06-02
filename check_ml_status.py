# check_ml_status.py
import sqlite3
import os
import json

# Check if ML is enabled
if os.path.exists('bot_control.json'):
    with open('bot_control.json', 'r') as f:
        settings = json.load(f)
    print(f"ML Enabled: {settings.get('use_machine_learning', False)}")

# Check if ML model exists
if os.path.exists('data/ml_model.pkl'):
    print("✅ ML model file exists")
    # Get file size and modification time
    import datetime
    stat = os.stat('data/ml_model.pkl')
    print(f"   Size: {stat.st_size} bytes")
    print(f"   Last updated: {datetime.datetime.fromtimestamp(stat.st_mtime)}")
else:
    print("❌ ML model not yet trained")

# Check ML performance metrics
if os.path.exists('data/sol_bot.db'):
    conn = sqlite3.connect('data/sol_bot.db')
    
    # Count trades for training
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM trades")
    trade_count = cursor.fetchone()[0]
    print(f"\nTotal trades for training: {trade_count}")
    
    # Check if ml_model_performance table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ml_model_performance'")
    if cursor.fetchone():
        cursor.execute("SELECT * FROM ml_model_performance ORDER BY timestamp DESC LIMIT 1")
        ml_perf = cursor.fetchone()
        if ml_perf:
            print(f"\nLatest ML Performance:")
            print(f"  Accuracy: {ml_perf[2]*100:.1f}%")
            print(f"  Precision: {ml_perf[3]*100:.1f}%")
            print(f"  Recall: {ml_perf[4]*100:.1f}%")
    else:
        print("\nML performance table not yet created")
    
    conn.close()