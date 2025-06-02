import os
import pickle
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta, UTC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

from config import BotConfiguration

logger = logging.getLogger('trading_bot.ml_model')

class MLModel:
    """
    Machine Learning model for predicting token performance
    """
    
    def __init__(self):
        """
        Initialize the machine learning model
        """
        self.model = None
        self.scaler = None
        self.features = [
            'volume_24h', 'liquidity_usd', 'price_usd',
            'mcap', 'holders', 'safety_score'
        ]
        self.model_path = os.path.join(BotConfiguration.DATA_DIR, 'ml_model.pkl')
        self.performance_stats = {
            'accuracy': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1': 0.0,
            'last_training': None,
            'training_samples': 0,
            'feature_importance': {}
        }
        
        # Try to load a pre-trained model if it exists
        self._load_model()
        
    def _load_model(self):
        """
        Load a pre-trained model if it exists
        """
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data.get('model')
                    self.scaler = data.get('scaler')
                    self.performance_stats = data.get('stats', self.performance_stats)
                logger.info(f"Loaded pre-trained model with accuracy: {self.performance_stats['accuracy']:.4f}")
                return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
        return False
    
    def _save_model(self):
        """
        Save the trained model
        """
        try:
            if self.model is not None:
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                with open(self.model_path, 'wb') as f:
                    pickle.dump({
                        'model': self.model,
                        'scaler': self.scaler,
                        'stats': self.performance_stats
                    }, f)
                logger.info("Model saved successfully")
                return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
        return False
    
    def prepare_features(self, token_data):
        """
        Prepare features for prediction
        
        :param token_data: Token data dictionary or DataFrame row
        :return: Prepared features as numpy array
        """
        features = []
        
        # Handle both dictionary and DataFrame row input
        if isinstance(token_data, dict):
            for feature in self.features:
                value = token_data.get(feature, 0.0)
                features.append(float(value) if value is not None else 0.0)
        else:
            for feature in self.features:
                if feature in token_data:
                    value = token_data[feature]
                    features.append(float(value) if value is not None else 0.0)
                else:
                    # Try alternative column names
                    if feature == 'mcap' and 'market_cap' in token_data:
                        value = token_data['market_cap']
                    elif feature == 'holders' and 'holder_count' in token_data:
                        value = token_data['holder_count']
                    else:
                        value = 0.0
                    features.append(float(value) if value is not None else 0.0)
        
        # Convert to numpy array and reshape
        return np.array(features).reshape(1, -1)
    
    def train(self, db):
        """
        Train the model using historical data
        
        :param db: Database instance
        :return: True if training successful, False otherwise
        """
        try:
            # Fetch historical data
            trades_df = db.get_trading_history(limit=1000)
            tokens_df = db.get_tokens(limit=1000)
            
            if trades_df.empty or tokens_df.empty:
                logger.warning("Not enough data for training")
                return False
            
            # Merge trading data with token data
            merged_df = pd.merge(trades_df, tokens_df, on='contract_address', how='inner')
            
            if merged_df.empty:
                logger.warning("No merged data available for training")
                return False
            
            # Prepare features and target
            X = merged_df[self.features].fillna(0)
            
            # Define success as trades that resulted in profit or not
            # Assuming trades with the same contract_address are grouped together
            contract_groups = merged_df.groupby('contract_address')
            
            # Calculate profit/loss for each contract
            results = []
            for contract, group in contract_groups:
                buys = group[group['action'] == 'BUY']
                sells = group[group['action'] == 'SELL']
                
                if not buys.empty and not sells.empty:
                    buy_value = buys['amount'].sum() * buys['price'].mean()
                    sell_value = sells['amount'].sum() * sells['price'].mean()
                    
                    # Profit ratio
                    profit_ratio = sell_value / buy_value if buy_value > 0 else 0
                    
                    # Success if profit_ratio > 1.2 (20% profit)
                    success = 1 if profit_ratio > 1.2 else 0
                    
                    # Get the token data (using first row)
                    token_data = group.iloc[0]
                    
                    # Add to results
                    results.append({
                        'contract_address': contract,
                        'success': success,
                        **{feature: token_data[feature] for feature in self.features if feature in token_data}
                    })
            
            # Convert results to DataFrame
            results_df = pd.DataFrame(results)
            
            if results_df.empty or len(results_df) < 10:
                logger.warning("Not enough trading results for training")
                return False
            
            # Prepare dataset
            X = results_df[self.features].fillna(0)
            y = results_df['success']
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Create and train the model
            pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('classifier', GradientBoostingClassifier(n_estimators=100, random_state=42))
            ])
            
            pipeline.fit(X_train, y_train)
            
            # Evaluate the model
            y_pred = pipeline.predict(X_test)
            
            self.model = pipeline
            self.scaler = pipeline.named_steps['scaler']
            
            # Update performance stats
            self.performance_stats['accuracy'] = accuracy_score(y_test, y_pred)
            self.performance_stats['precision'] = precision_score(y_test, y_pred, zero_division=0)
            self.performance_stats['recall'] = recall_score(y_test, y_pred, zero_division=0)
            self.performance_stats['f1'] = f1_score(y_test, y_pred, zero_division=0)
            self.performance_stats['last_training'] = datetime.now(UTC).isoformat()
            self.performance_stats['training_samples'] = len(X)
            
            # Get feature importance
            classifier = self.model.named_steps['classifier']
            if hasattr(classifier, 'feature_importances_'):
                importances = classifier.feature_importances_
                feature_importance = {}
                for i, feature in enumerate(self.features):
                    if i < len(importances):
                        feature_importance[feature] = float(importances[i])
                self.performance_stats['feature_importance'] = feature_importance
            
            logger.info(f"Model trained successfully with {len(X)} samples")
            logger.info(f"Accuracy: {self.performance_stats['accuracy']:.4f}, "
                      f"Precision: {self.performance_stats['precision']:.4f}, "
                      f"Recall: {self.performance_stats['recall']:.4f}, "
                      f"F1: {self.performance_stats['f1']:.4f}")
            
            # Save the trained model
            self._save_model()
            
            return True
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def predict(self, token_data):
        """
        Predict if a token will be profitable
        
        :param token_data: Token data dictionary
        :return: Prediction score (0 to 1), confidence, and features importance
        """
        if self.model is None:
            logger.warning("Model not trained yet")
            return 0.5, 0.0, {}
        
        try:
            # Prepare features
            X = self.prepare_features(token_data)
            
            # Get the prediction probability
            proba = self.model.predict_proba(X)[0]
            
            # Prediction (1 = success, 0 = failure)
            prediction = proba[1]
            
            # Confidence (distance from 0.5)
            confidence = abs(prediction - 0.5) * 2.0
            
            # Get feature importance if available
            feature_importance = self.performance_stats.get('feature_importance', {})
            
            return prediction, confidence, feature_importance
            
        except Exception as e:
            logger.error(f"Error predicting: {e}")
            return 0.5, 0.0, {}
    
    def get_performance_stats(self):
        """
        Get model performance statistics
        
        :return: Dictionary with performance stats
        """
        return self.performance_stats