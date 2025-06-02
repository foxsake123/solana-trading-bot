"""
ML Model Manager - Ensures ML learning transfers between simulation and real trading
"""
import os
import json
import pickle
import pandas as pd
import sqlite3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ml_model_manager')

class MLModelManager:
    def __init__(self):
        self.model_path = 'data/ml_model.pkl'
        self.training_data_path = 'data/ml_training_data.csv'
        
    def save_training_data(self, simulation_mode=True):
        """Save training data from database for ML model"""
        db_path = 'data/sol_bot.db'
        
        if not os.path.exists(db_path):
            logger.error("Database not found")
            return
        
        conn = sqlite3.connect(db_path)
        
        try:
            # Get all completed trades (both simulation and real)
            query = """
            SELECT 
                t1.contract_address,
                t1.action as buy_action,
                t1.price as buy_price,
                t1.amount as buy_amount,
                t1.timestamp as buy_time,
                t2.action as sell_action,
                t2.price as sell_price,
                t2.amount as sell_amount,
                t2.timestamp as sell_time,
                t1.is_simulation,
                tok.volume_24h,
                tok.liquidity_usd,
                tok.mcap,
                tok.holders,
                tok.safety_score
            FROM trades t1
            JOIN trades t2 ON t1.contract_address = t2.contract_address
            LEFT JOIN tokens tok ON t1.contract_address = tok.contract_address
            WHERE t1.action = 'BUY' AND t2.action = 'SELL'
            AND t2.timestamp > t1.timestamp
            """
            
            df = pd.read_sql_query(query, conn)
            
            if not df.empty:
                # Calculate profit/loss for each trade
                df['profit_ratio'] = df['sell_price'] / df['buy_price']
                df['profit_percentage'] = (df['profit_ratio'] - 1) * 100
                df['success'] = (df['profit_ratio'] > 1.1).astype(int)  # Success if > 10% profit
                
                # Save both simulation and real data
                df.to_csv(self.training_data_path, index=False)
                logger.info(f"Saved {len(df)} trades for ML training")
                logger.info(f"Simulation trades: {len(df[df['is_simulation'] == 1])}")
                logger.info(f"Real trades: {len(df[df['is_simulation'] == 0])}")
                
                return df
            else:
                logger.warning("No completed trades found for training")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error saving training data: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def train_model(self, include_simulation=True, include_real=True):
        """Train ML model on historical data"""
        if not os.path.exists(self.training_data_path):
            logger.warning("No training data found. Saving from database...")
            self.save_training_data()
        
        try:
            df = pd.read_csv(self.training_data_path)
            
            if df.empty:
                logger.warning("No training data available")
                return
            
            # Filter based on what we want to include
            if not include_simulation:
                df = df[df['is_simulation'] == 0]
            if not include_real:
                df = df[df['is_simulation'] == 1]
            
            logger.info(f"Training on {len(df)} trades")
            
            # Features for training
            features = ['volume_24h', 'liquidity_usd', 'mcap', 'holders', 'safety_score']
            
            # Handle missing values
            df[features] = df[features].fillna(0)
            
            X = df[features]
            y = df['success']
            
            if len(df) < 10:
                logger.warning("Not enough data for training (need at least 10 trades)")
                return
            
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train model
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            
            # Evaluate
            predictions = model.predict(X_test)
            accuracy = accuracy_score(y_test, predictions)
            
            logger.info(f"Model accuracy: {accuracy:.2%}")
            
            # Save model
            model_data = {
                'model': model,
                'features': features,
                'accuracy': accuracy,
                'trained_on': len(df),
                'timestamp': datetime.now().isoformat()
            }
            
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {self.model_path}")
            
            # Feature importance
            importance = pd.DataFrame({
                'feature': features,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            logger.info("Feature importance:")
            for _, row in importance.iterrows():
                logger.info(f"  {row['feature']}: {row['importance']:.3f}")
                
        except Exception as e:
            logger.error(f"Error training model: {e}")
    
    def load_model(self):
        """Load the trained ML model"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                logger.info(f"Loaded model trained on {model_data['trained_on']} trades")
                logger.info(f"Model accuracy: {model_data['accuracy']:.2%}")
                logger.info(f"Trained at: {model_data['timestamp']}")
                
                return model_data
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                return None
        else:
            logger.warning("No trained model found")
            return None
    
    def predict_trade_success(self, token_data):
        """Predict if a trade will be successful"""
        model_data = self.load_model()
        
        if not model_data:
            return 0.5, "No model available"
        
        try:
            model = model_data['model']
            features = model_data['features']
            
            # Prepare features
            X = pd.DataFrame([{
                'volume_24h': token_data.get('volume_24h', 0),
                'liquidity_usd': token_data.get('liquidity_usd', 0),
                'mcap': token_data.get('market_cap', 0),
                'holders': token_data.get('holders', 0),
                'safety_score': token_data.get('safety_score', 50)
            }])[features]
            
            # Predict probability
            proba = model.predict_proba(X)[0]
            success_probability = proba[1]  # Probability of success
            
            # Generate recommendation
            if success_probability > 0.7:
                recommendation = "Strong Buy"
            elif success_probability > 0.6:
                recommendation = "Buy"
            elif success_probability < 0.4:
                recommendation = "Avoid"
            else:
                recommendation = "Neutral"
            
            return success_probability, recommendation
            
        except Exception as e:
            logger.error(f"Error predicting: {e}")
            return 0.5, "Prediction error"

# Usage example
if __name__ == "__main__":
    manager = MLModelManager()
    
    # Save current training data
    df = manager.save_training_data()
    
    # Train model on all data (simulation + real)
    manager.train_model(include_simulation=True, include_real=True)
    
    # Load and check model
    model_data = manager.load_model()
    
    if model_data:
        print(f"\nModel ready for use!")
        print(f"Trained on {model_data['trained_on']} trades")
        print(f"Accuracy: {model_data['accuracy']:.2%}")
        print("\nThe model will work for both simulation and real trading!")