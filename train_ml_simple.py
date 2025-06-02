# train_ml_simple.py
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import pickle
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ml_trainer')

def calculate_safety_scores():
    """Calculate and update safety scores for all tokens"""
    conn = sqlite3.connect('data/sol_bot.db')
    
    # Get all tokens
    tokens = pd.read_sql_query("SELECT * FROM tokens", conn)
    
    for idx, token in tokens.iterrows():
        # Calculate safety score based on available data
        safety_score = 0.0
        
        # Liquidity factor (0-40 points)
        liquidity = token.get('liquidity_usd', 0)
        if liquidity >= 100000:
            safety_score += 40
        elif liquidity >= 50000:
            safety_score += 30
        elif liquidity >= 10000:
            safety_score += 20
        elif liquidity >= 5000:
            safety_score += 10
        
        # Volume factor (0-30 points)
        volume = token.get('volume_24h', 0)
        if volume >= 100000:
            safety_score += 30
        elif volume >= 50000:
            safety_score += 20
        elif volume >= 10000:
            safety_score += 10
        
        # Holders factor (0-30 points)
        holders = token.get('holders', 0)
        if holders >= 1000:
            safety_score += 30
        elif holders >= 500:
            safety_score += 20
        elif holders >= 100:
            safety_score += 10
        elif holders >= 50:
            safety_score += 5
        
        # Update the token with safety score
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tokens SET safety_score = ? WHERE contract_address = ?",
            (safety_score, token['contract_address'])
        )
    
    conn.commit()
    conn.close()
    logger.info("Updated safety scores for all tokens")

def train_simple_model():
    """Train a simple ML model with available data"""
    
    # First calculate safety scores
    calculate_safety_scores()
    
    conn = sqlite3.connect('data/sol_bot.db')
    
    # Get trades with outcomes
    query = """
    SELECT 
        t1.contract_address,
        t1.amount as buy_amount,
        t1.price as buy_price,
        t2.amount as sell_amount,
        t2.price as sell_price,
        tk.volume_24h,
        tk.liquidity_usd,
        tk.price_usd,
        tk.mcap,
        tk.holders,
        tk.safety_score
    FROM trades t1
    JOIN trades t2 ON t1.contract_address = t2.contract_address
    JOIN tokens tk ON t1.contract_address = tk.contract_address
    WHERE t1.action = 'BUY' AND t2.action = 'SELL'
    AND t1.timestamp < t2.timestamp
    """
    
    data = pd.read_sql_query(query, conn)
    
    if len(data) < 10:
        logger.warning(f"Only {len(data)} completed trades. Need more data for training.")
        conn.close()
        return False
    
    # Calculate profit/loss
    data['profit_ratio'] = (data['sell_price'] / data['buy_price'])
    data['success'] = (data['profit_ratio'] > 1.15).astype(int)  # 15% profit threshold
    
    # Prepare features
    feature_columns = ['volume_24h', 'liquidity_usd', 'price_usd', 'mcap', 'holders', 'safety_score']
    X = data[feature_columns].fillna(0)
    y = data['success']
    
    # Train a simple model
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    
    logger.info(f"Model Performance:")
    logger.info(f"  Accuracy: {accuracy:.2%}")
    logger.info(f"  Precision: {precision:.2%}")
    logger.info(f"  Recall: {recall:.2%}")
    
    # Save model
    os.makedirs('data', exist_ok=True)
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'features': feature_columns,
        'stats': {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'training_samples': len(X_train),
            'last_training': datetime.now().isoformat()
        }
    }
    
    with open('data/ml_model.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    logger.info("✅ Model saved successfully!")
    
    # Feature importance
    importances = model.feature_importances_
    feature_importance = dict(zip(feature_columns, importances))
    logger.info("\nFeature Importance:")
    for feature, importance in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {feature}: {importance:.3f}")
    
    conn.close()
    return True

if __name__ == "__main__":
    print("🤖 Training ML Model with available data...")
    success = train_simple_model()
    
    if success:
        print("\n✅ ML Model trained successfully!")
        print("The bot will now use ML predictions for trading decisions.")
    else:
        print("\n❌ Need more completed trades for training.")
        print("Let the bot run longer to collect more data.")